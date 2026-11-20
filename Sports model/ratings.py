#!/usr/bin/env python3
"""
Team ratings, rebuilt before every game day from earlier games only.

Each team gets three numbers:
    offence   points it scores per 100 possessions above an average team
    defence   points it allows per 100 possessions above an average team (negative = good)
    pace      possessions per 48 minutes above an average team

They are fitted so that every past game is explained by BOTH teams at once (a team that
scored 120 on the best defence gets more credit than one that scored 120 on the worst),
with three rules that keep them honest:
    * recent games count more   - a game's weight halves every `half_life` days
    * small samples are doubted - every rating is pulled toward average (`ridge`)
    * a new season is a new team- last season's games are cut to `carry` of their weight

The maths is a weighted ridge regression. Because the weights fade at a steady rate, the
running totals can be faded and added to one day at a time, so a whole walk-forward pass
over four seasons takes well under a second.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class RatingConfig:
    half_life: float = 45.0        # days for a game's weight to halve (within a season)
    carry: float = 0.35            # weight kept by last season's games when a new one starts
    ridge_eff: float = 14.0        # pull toward average for offence / defence
    ridge_pace: float = 6.0        # pull toward average for pace
    luck3: float = 0.0             # share of 3-point shooting luck removed (0 = none, 1 = all)
    cap_eff: float = 45.0          # a single game's efficiency can't be further than this from average
    drift_half_life: float = 0.0   # days; >0 tracks league-wide scoring/pace drift (0 = off)
    drift_prior: float = 20.0      # games of "no drift" mixed in, so a few odd nights don't move it


class _Ridge:
    """Running weighted ridge regression:  minimise  sum w (y - x.b)^2 + ridge |b_teams|^2."""

    def __init__(self, n_free: int, n_teams_params: int, ridge: float):
        k = n_free + n_teams_params
        self.A = np.zeros((k, k))
        self.b = np.zeros(k)
        self.pen = np.diag([0.0] * n_free + [ridge] * n_teams_params)
        self.n_free = n_free
        self.weight = 0.0

    def fade(self, factor: float) -> None:
        self.A *= factor
        self.b *= factor
        self.weight *= factor

    def add(self, idx: list[int], vals: list[float], y: float, w: float = 1.0) -> None:
        for i, vi in zip(idx, vals):
            self.b[i] += w * vi * y
            for j, vj in zip(idx, vals):
                self.A[i, j] += w * vi * vj
        self.weight += w

    def solve(self) -> np.ndarray:
        A = self.A + self.pen
        # Before any data the free terms have nothing to pin them down.
        A = A + np.diag([1e-6] * A.shape[0])
        return np.linalg.solve(A, self.b)


class Ratings:
    """The league's ratings as of one moment. Feed it games in date order."""

    def __init__(self, teams: list[str], cfg: RatingConfig = RatingConfig()):
        self.cfg = cfg
        self.teams = sorted(teams)
        self.ix = {t: i for i, t in enumerate(self.teams)}
        n = len(self.teams)
        # efficiency: [league average, home edge, offence x n, defence x n]
        self.eff = _Ridge(2, 2 * n, cfg.ridge_eff)
        # pace: [league average, pace x n]
        self.pace = _Ridge(1, n, cfg.ridge_pace)
        self.n = n
        self.season = None
        self.day = None
        self.games = {t: 0.0 for t in self.teams}        # faded count of games per team
        self.fg3 = np.array([36.0, 100.0])               # league 3-pointers made, attempted (faded)
        # League-wide drift: recent average of (actual - predicted) for efficiency and pace.
        # Team ratings move slowly on purpose; this catches the whole league scoring more or
        # less than it did a month ago (officiating, rule tweaks, time of season).
        self.drift = np.zeros(3)                         # [sum eff miss, sum pace miss, games]
        self._solved = None

    # ---- time ---------------------------------------------------------
    def advance(self, day: pd.Timestamp, season: int) -> None:
        """Fade everything to `day`. Call before reading ratings or adding that day's games."""
        if self.day is None:
            self.day, self.season = day, season
            return
        if season != self.season:
            factor = self.cfg.carry
        else:
            factor = 0.5 ** (max((day - self.day).days, 0) / self.cfg.half_life)
        if factor != 1.0:
            self.eff.fade(factor)
            self.pace.fade(factor)
            self.fg3 *= factor
            for t in self.games:
                self.games[t] *= factor
            self._solved = None
        if self.cfg.drift_half_life > 0:
            if season != self.season:
                self.drift *= 0.0              # a new season starts with no drift
            else:
                self.drift *= 0.5 ** (max((day - self.day).days, 0) / self.cfg.drift_half_life)
        self.day, self.season = day, season

    def drift_eff(self) -> float:
        return float(self.drift[0] / (self.drift[2] + self.cfg.drift_prior))

    def drift_pace(self) -> float:
        return float(self.drift[1] / (self.drift[2] + self.cfg.drift_prior))

    def note_result(self, g, pred: dict) -> None:
        """Record how far the league-wide part of a prediction missed (call before add_game)."""
        if self.cfg.drift_half_life <= 0 or not np.isfinite(g.poss) or g.poss <= 0:
            return
        eff_miss = ((g.home_eff - pred["raw_eff_home"]) + (g.away_eff - pred["raw_eff_away"])) / 2
        self.drift += np.array([eff_miss, g.pace - pred["raw_pace"], 1.0])

    # ---- learning -----------------------------------------------------
    def add_game(self, g) -> None:
        """Add one played game (a row of core.games_table)."""
        if not np.isfinite(g.poss) or g.poss <= 0:
            return
        h, a = self.ix[g.home], self.ix[g.away]
        n = self.n
        home_edge = 0.0 if g.neutral else 0.5
        lg3 = self.fg3[0] / self.fg3[1]
        for (team, opp, edge, pts, m3, a3) in (
                (h, a, home_edge, g.home_score, g.home_fg3m, g.home_fg3a),
                (a, h, -home_edge, g.away_score, g.away_fg3m, g.away_fg3a)):
            if self.cfg.luck3:
                # Swap part of the made-minus-expected 3-pointers for league-average shooting.
                pts = pts - self.cfg.luck3 * 3.0 * (m3 - a3 * lg3)
            eff = 100.0 * pts / g.poss
            mean = self.league_eff()
            eff = float(np.clip(eff, mean - self.cfg.cap_eff, mean + self.cfg.cap_eff))
            self.eff.add([0, 1, 2 + team, 2 + n + opp], [1.0, edge, 1.0, 1.0], eff)
        self.pace.add([0, 1 + h, 1 + a], [1.0, 1.0, 1.0], float(g.pace))
        self.fg3 += np.array([g.home_fg3m + g.away_fg3m, g.home_fg3a + g.away_fg3a], dtype=float)
        self.games[g.home] += 1
        self.games[g.away] += 1
        self._solved = None

    # ---- reading ------------------------------------------------------
    def _solve(self):
        if self._solved is None:
            if self.eff.weight < 1:
                e = np.zeros(2 + 2 * self.n)
                e[0], e[1] = 113.0, 2.5
                p = np.zeros(1 + self.n)
                p[0] = 100.0
            else:
                e, p = self.eff.solve(), self.pace.solve()
            self._solved = (e, p)
        return self._solved

    def league_eff(self) -> float:
        return float(self._solve()[0][0])

    def league_pace(self) -> float:
        return float(self._solve()[1][0])

    def home_edge(self) -> float:
        """Home advantage in points per 100 possessions (home offence + home defence)."""
        return float(self._solve()[0][1])

    def team(self, t: str) -> dict:
        e, p = self._solve()
        i = self.ix[t]
        return {"off": float(e[2 + i]), "def": float(e[2 + self.n + i]),
                "net": float(e[2 + i] - e[2 + self.n + i]), "pace": float(p[1 + i]),
                "games": self.games[t]}

    def table(self) -> pd.DataFrame:
        rows = [{"team": t, **self.team(t)} for t in self.teams]
        return pd.DataFrame(rows).sort_values("net", ascending=False).reset_index(drop=True)

    def predict(self, home: str, away: str, neutral: bool = False) -> dict:
        """Ratings-only expectation for one game (no rest, injuries or calibration yet)."""
        e, p = self._solve()
        h, a, n = self.ix[home], self.ix[away], self.n
        edge = 0.0 if neutral else 0.5 * e[1]
        d_eff, d_pace = (self.drift_eff(), self.drift_pace()) if self.cfg.drift_half_life > 0 else (0.0, 0.0)
        pace = p[0] + p[1 + h] + p[1 + a] + d_pace
        eff_h = e[0] + e[2 + h] + e[2 + n + a] + edge + d_eff
        eff_a = e[0] + e[2 + a] + e[2 + n + h] - edge + d_eff
        pts_h, pts_a = pace * eff_h / 100.0, pace * eff_a / 100.0
        return {"raw_pace": float(pace), "raw_eff_home": float(eff_h), "raw_eff_away": float(eff_a),
                "raw_home": float(pts_h), "raw_away": float(pts_a),
                "raw_margin": float(pts_h - pts_a), "raw_total": float(pts_h + pts_a),
                "net_home": float(e[2 + h] - e[2 + n + h]), "net_away": float(e[2 + a] - e[2 + n + a]),
                "pace_home": float(p[1 + h]), "pace_away": float(p[1 + a]),
                "games_home": self.games[home], "games_away": self.games[away]}


def walk_forward(games: pd.DataFrame, cfg: RatingConfig = RatingConfig(),
                 return_state: bool = False):
    """Predict every game from the games before it. Returns `games` with raw_* columns added.

    Games are taken a day at a time: all of a day's games are predicted from the ratings as
    they stood that morning, and only then added to the ratings.
    """
    teams = sorted(set(games.home) | set(games.away))
    r = Ratings(teams, cfg)
    out = []
    for (day, season), block in games.groupby(["date", "season"], sort=True):
        r.advance(day, season)
        preds = []
        for g in block.itertuples(index=False):
            p = r.predict(g.home, g.away, bool(g.neutral))
            preds.append(p)
            out.append({"game_id": g.game_id, **p,
                        "lg_eff": r.league_eff(), "lg_pace": r.league_pace(),
                        "home_edge": r.home_edge()})
        for g, p in zip(block.itertuples(index=False), preds):
            if g.played:
                r.note_result(g, p)
        for g in block.itertuples(index=False):
            if g.played:
                r.add_game(g)
    res = games.merge(pd.DataFrame(out), on="game_id", how="left")
    return (res, r) if return_state else res
