#!/usr/bin/env python3
"""
Who is playing tonight, and what is that worth?

Team ratings only know how a team has played with whoever was on the floor. This module
measures the gap between the lineup the ratings have "seen" and the lineup expected
tonight, so a star sitting out (or coming back) moves the prediction.

For every team before every game it works out:
    seen      the share of minutes each player has had in the games behind the team rating
              (faded exactly like the rating itself, missed games counting as zero)
    tonight   the minutes each available player is expected to get, scaled to 240
    value     each player's box-score production per minute, from his earlier games only

    lineup gap = (average value per minute tonight) - (average value per minute seen)

The gap is in box-score units; the model learns from past games how many points of margin
and total one unit is worth. Three ways of deciding who is "available" are produced:
    actual     who really played (known about 30 minutes before tip-off, when lineups lock)
    expected   a guess made from recent absences only (known the day before)
    live       tonight's injury report (used for real predictions)
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

import numpy as np
import pandas as pd

TEAM_MINUTES = 240.0


@dataclass(frozen=True)
class PlayerConfig:
    value_half_life: float = 200.0   # days for a game's weight in a player's value to halve
    value_carry: float = 0.6         # weight kept by earlier seasons
    prior_minutes: float = 250.0     # minutes of a typical bench player mixed into every value
    prior_value: float = 0.30        # that bench player's production per minute
    plus_minus_weight: float = 0.0   # share of on-court plus/minus blended into the value
    minutes_span: float = 6.0        # games in the moving average of a player's minutes
    max_minutes: float = 38.0
    roster_gap: int = 12             # team games missed in a row before a player is dropped
    team_half_life: float = 60.0     # must match the team ratings' half_life
    team_carry: float = 0.35         # must match the team ratings' carry


# Chance a rotation player plays tonight given how many of his team's games he has just
# missed in a row. Measured on the 2023-24 and 2024-25 seasons (see experiments/).
PLAY_AFTER_MISSING = {0: 0.92, 1: 0.52, 2: 0.31, 3: 0.23, 4: 0.17, 5: 0.16}
PLAY_AFTER_LONG = [(8, 0.10), (12, 0.07), (10 ** 9, 0.04)]


def play_after_missing(streak: int) -> float:
    if streak in PLAY_AFTER_MISSING:
        return PLAY_AFTER_MISSING[streak]
    for upto, p in PLAY_AFTER_LONG:
        if streak <= upto:
            return p
    return 0.04


def game_score(p) -> float:
    """John Hollinger's Game Score: one number for a box-score line."""
    return (p.pts + 0.4 * p.fgm - 0.7 * p.fga - 0.4 * (p.fta - p.ftm) + 0.7 * p.oreb
            + 0.3 * p.dreb + p.stl + 0.7 * p.ast + 0.7 * p.blk - 0.4 * p.pf - p.tov)


class _Player:
    __slots__ = ("num", "den", "pm", "day", "season", "team", "name", "mins", "n")

    def __init__(self):
        self.num = self.den = self.pm = 0.0     # faded production, minutes, plus/minus
        self.day = self.season = None
        self.team = None                        # team of his latest game
        self.name = ""
        self.mins = 0.0                         # moving average of minutes (any team)
        self.n = 0


class _Spot:
    """One player's history with one team."""
    __slots__ = ("seen", "mins", "games", "last")

    def __init__(self):
        self.seen = 0.0       # faded minutes in the games behind the team rating
        self.mins = 0.0       # moving average of minutes when he plays for this team
        self.games = 0
        self.last = -1        # team game number of his latest appearance


class _Team:
    __slots__ = ("spots", "weight", "count", "day", "season")

    def __init__(self):
        self.spots: dict[str, _Spot] = defaultdict(_Spot)
        self.weight = 0.0     # faded number of games
        self.count = 0        # games played, ever
        self.day = self.season = None


class Lineups:
    """Player values and team lineups as of one moment. Feed it games in date order."""

    def __init__(self, cfg: PlayerConfig = PlayerConfig()):
        self.cfg = cfg
        self.players: dict[str, _Player] = defaultdict(_Player)
        self.teams: dict[str, _Team] = defaultdict(_Team)

    # ---- fading -------------------------------------------------------
    def _fade_player(self, p: _Player, day, season) -> None:
        if p.day is not None:
            if season != p.season:
                f = self.cfg.value_carry ** max(season - p.season, 1)
            else:
                f = 0.5 ** (max((day - p.day).days, 0) / self.cfg.value_half_life)
            p.num *= f
            p.den *= f
            p.pm *= f
        p.day, p.season = day, season

    def _fade_team(self, t: _Team, day, season) -> None:
        if t.day is not None:
            if season != t.season:
                f = self.cfg.team_carry
            else:
                f = 0.5 ** (max((day - t.day).days, 0) / self.cfg.team_half_life)
            t.weight *= f
            for s in t.spots.values():
                s.seen *= f
        t.day, t.season = day, season

    # ---- reading ------------------------------------------------------
    def value(self, pid: str) -> float:
        """Production per minute, pulled toward a typical bench player when minutes are few."""
        p = self.players.get(pid)
        c = self.cfg
        if p is None:
            return c.prior_value
        box = (p.num + c.prior_minutes * c.prior_value) / (p.den + c.prior_minutes)
        if c.plus_minus_weight:
            # plus/minus per minute, on the same scale as production (league average about 0)
            box += c.plus_minus_weight * p.pm / (p.den + 4 * c.prior_minutes)
        return box

    def roster(self, team: str) -> list[str]:
        """Players who count as on the team now: appeared for it within the last `roster_gap`
        team games and have not played for another team since."""
        t = self.teams[team]
        return [pid for pid, s in t.spots.items()
                if s.games > 0 and t.count - 1 - s.last < self.cfg.roster_gap
                and self.players[pid].team == team]

    def missed(self, team: str, pid: str) -> int:
        """Team games in a row this player has just missed."""
        t = self.teams[team]
        s = t.spots.get(pid)
        return t.count if s is None or s.last < 0 else t.count - 1 - s.last

    def _minutes_if_playing(self, team: str, pid: str) -> float:
        s = self.teams[team].spots.get(pid)
        if s is not None and s.games >= 2:
            return s.mins
        p = self.players.get(pid)
        other = p.mins * 0.85 if p is not None and p.n >= 3 else 14.0   # new to this team
        if s is not None and s.games == 1:
            return 0.5 * s.mins + 0.5 * other
        return other

    def _allocate(self, want: dict[str, float]) -> dict[str, float]:
        """Scale expected minutes to 240 a team, nobody above max_minutes."""
        mins = {k: v for k, v in want.items() if v > 0}
        if not mins:
            return {}
        cap = self.cfg.max_minutes
        fixed: dict[str, float] = {}
        for _ in range(6):
            free = {k: v for k, v in mins.items() if k not in fixed}
            room = TEAM_MINUTES - sum(fixed.values())
            total = sum(free.values())
            if not free or total <= 0:
                break
            scale = room / total
            over = [k for k, v in free.items() if v * scale > cap]
            if not over:
                return {**fixed, **{k: v * scale for k, v in free.items()}}
            for k in over:
                fixed[k] = cap
        return fixed

    def gap(self, team: str, day, season, chance: dict[str, float]) -> dict:
        """Lineup gap for `team` given each player's chance of playing tonight.

        chance: {player_id: 0..1}. Players not listed are taken as not playing.
        """
        t = self.teams[team]
        self._fade_team(t, day, season)
        seen_total = sum(s.seen for s in t.spots.values())
        if seen_total <= 0 or t.weight < 1.0:
            return {"gap": 0.0, "tonight": np.nan, "seen": np.nan, "out": [], "known": 0.0}
        seen = sum(s.seen * self.value(pid) for pid, s in t.spots.items()) / seen_total
        mins = self._allocate({pid: c * self._minutes_if_playing(team, pid)
                               for pid, c in chance.items() if c > 0})
        total = sum(mins.values())
        if total <= 0:
            return {"gap": 0.0, "tonight": np.nan, "seen": seen, "out": [], "known": 0.0}
        tonight = sum(m * self.value(pid) for pid, m in mins.items()) / total
        # the players whose absence costs most, for the printed card
        out = []
        for pid, s in t.spots.items():
            usual = s.seen / t.weight
            now = mins.get(pid, 0.0)
            if usual - now >= 6 and chance.get(pid, 0.0) < 0.75:
                out.append((self.players[pid].name, round(usual, 1), round(chance.get(pid, 0.0), 2),
                            round(self.value(pid), 3)))
        out.sort(key=lambda x: -x[1] * x[3])
        return {"gap": (tonight - seen) * TEAM_MINUTES, "tonight": tonight, "seen": seen,
                "out": out[:5], "known": t.weight}

    def expected_chances(self, team: str) -> dict[str, float]:
        """Chance each roster player plays, judged only from recent absences."""
        return {pid: play_after_missing(self.missed(team, pid)) for pid in self.roster(team)}

    # ---- learning -----------------------------------------------------
    def add_game(self, team: str, day, season, rows) -> None:
        """Add one team's box score for one game. rows: that team's player rows."""
        t = self.teams[team]
        self._fade_team(t, day, season)
        alpha = 2.0 / (self.cfg.minutes_span + 1.0)
        for r in rows:
            if r.dnp or r.minutes <= 0:
                continue
            p = self.players[r.player_id]
            self._fade_player(p, day, season)
            p.num += game_score(r)
            p.den += r.minutes
            p.pm += r.plus_minus
            p.team = team
            if len(r.name) > len(p.name):
                p.name = r.name
            p.mins = r.minutes if p.n == 0 else p.mins + alpha * (r.minutes - p.mins)
            p.n += 1
            s = t.spots[r.player_id]
            s.seen += r.minutes
            s.mins = r.minutes if s.games == 0 else s.mins + alpha * (r.minutes - s.mins)
            s.games += 1
            s.last = t.count
        t.weight += 1.0
        t.count += 1
        # forget players long gone, so rosters stay small
        if t.count % 20 == 0:
            for pid in [k for k, s in t.spots.items() if s.seen < 0.5 and t.count - s.last > 40]:
                del t.spots[pid]


def walk_forward(games: pd.DataFrame, players: pd.DataFrame,
                 cfg: PlayerConfig = PlayerConfig(), return_state: bool = False):
    """Lineup gaps for every game, from earlier games only.

    Adds to `games`:  gap_act_home/away (who really played)  and
                      gap_exp_home/away (guessed from recent absences).
    """
    L = Lineups(cfg)
    by_game = {k: list(v.itertuples(index=False)) for k, v in players.groupby("game_id", sort=False)}
    out = []
    for g in games.itertuples(index=False):
        rows = by_game.get(g.game_id, [])
        rec = {"game_id": g.game_id}
        for side in ("home", "away"):
            team = getattr(g, side)
            mine = [r for r in rows if r.team == team]
            exp = L.gap(team, g.date, g.season, L.expected_chances(team))
            rec[f"gap_exp_{side}"] = exp["gap"]
            if g.played and mine:
                played = {r.player_id: 1.0 for r in mine if not r.dnp and r.minutes > 0}
                rec[f"gap_act_{side}"] = L.gap(team, g.date, g.season, played)["gap"]
            else:
                rec[f"gap_act_{side}"] = np.nan
        out.append(rec)
        if g.played:
            for side in ("home", "away"):
                team = getattr(g, side)
                L.add_game(team, g.date, g.season, [r for r in rows if r.team == team])
    res = games.merge(pd.DataFrame(out), on="game_id", how="left")
    return (res, L) if return_state else res
