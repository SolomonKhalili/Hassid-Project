#!/usr/bin/env python3
"""
The prediction model: team ratings + who is playing + schedule -> score, margin, total,
and the chances that go with them.

Three layers, each one checked on games it had not seen:

  1. ratings.py   offence, defence and pace for every team  -> a first guess at the score
  2. players.py   the lineup gap (who is in or out tonight)
  3. this file    a small regression that learns, from past games, how to turn layers 1-2
                  plus back-to-backs and playoffs into the final margin and total, and how
                  wide the misses are (which is what turns a number into a probability)

walk_forward() replays history: every game is predicted using only what was known before
it. fit() learns from everything to date and is what today's predictions use.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

import players as players_mod
import pricing
import ratings as ratings_mod


@dataclass(frozen=True)
class ModelConfig:
    ratings: ratings_mod.RatingConfig = ratings_mod.RatingConfig(
        half_life=60.0, carry=0.35, ridge_eff=4.0, ridge_pace=2.0, luck3=0.25,
        drift_half_life=10.0, drift_prior=10.0)
    players: players_mod.PlayerConfig = players_mod.PlayerConfig(team_half_life=60.0, team_carry=0.35)
    min_games: float = 3.0         # games behind both teams' ratings before a game is learned from
    min_train: int = 400           # games needed before the regression replaces the plain ratings
    ridge: float = 1.0             # keeps the small regression's weights from chasing noise
    burn_in_season: int = 2024     # first season only warms the ratings up; never scored


MARGIN_FEATURES = ["raw_margin", "home_ind", "gap_d", "b2b_d"]
TOTAL_FEATURES = ["raw_total", "one", "gap_s", "playoff"]
# The three views of "who is playing" (see players.py).
VARIANTS = {"act": "gap_act", "exp": "gap_exp", "none": None}


# ----------------------------------------------------------------------
# Features
# ----------------------------------------------------------------------

def build_features(games: pd.DataFrame, player_rows: pd.DataFrame,
                   cfg: ModelConfig = ModelConfig(), return_state: bool = False):
    """Everything known before each game, one row per game (played or not)."""
    f, lineups = players_mod.walk_forward(games, player_rows, cfg.players, return_state=True)
    f, rate = ratings_mod.walk_forward(f, cfg.ratings, return_state=True)
    f = add_columns(f)
    return (f, rate, lineups) if return_state else f


def add_columns(f: pd.DataFrame) -> pd.DataFrame:
    f = f.copy()
    f["one"] = 1.0
    f["home_ind"] = 1.0 - f.neutral
    f["b2b_d"] = f.home_b2b - f.away_b2b
    f["playoff"] = (f.season_type != 2).astype(float)
    for name, col in VARIANTS.items():
        if col is None:
            f["gap_d_none"] = 0.0
            f["gap_s_none"] = 0.0
        else:
            f[f"gap_d_{name}"] = f[f"{col}_home"] - f[f"{col}_away"]
            f[f"gap_s_{name}"] = f[f"{col}_home"] + f[f"{col}_away"]
    return f


def _design(f: pd.DataFrame, cols: list[str], variant: str) -> np.ndarray:
    """Feature matrix, with gap_d / gap_s taken from the chosen view of who is playing."""
    names = [f"{c}_{variant}" if c in ("gap_d", "gap_s") else c for c in cols]
    return f[names].to_numpy(float)


# ----------------------------------------------------------------------
# The small regression
# ----------------------------------------------------------------------

@dataclass
class Fit:
    """Weights for margin and total, and how wide the misses were."""
    margin_w: np.ndarray
    total_w: np.ndarray
    margin_sd: float
    total_sd: float
    n: int
    variant: str = "act"

    def predict(self, f: pd.DataFrame) -> pd.DataFrame:
        m = _design(f, MARGIN_FEATURES, self.variant) @ self.margin_w
        t = _design(f, TOTAL_FEATURES, self.variant) @ self.total_w
        return pd.DataFrame({"pred_margin": m, "pred_total": t,
                             "pred_home": (t + m) / 2, "pred_away": (t - m) / 2,
                             "sd_margin": self.margin_sd, "sd_total": self.total_sd}, index=f.index)


def _ridge(X: np.ndarray, y: np.ndarray, lam: float, anchor: np.ndarray) -> np.ndarray:
    """Least squares pulled gently toward `anchor` (the plain-ratings answer)."""
    sd = X.std(axis=0)
    pen = lam * sd ** 2                          # constant columns (sd 0) are not penalised
    # The tiny extra term keeps a column that is all zeros so far (no playoff games yet)
    # from breaking the solve; its weight simply stays at zero.
    A = X.T @ X + np.diag(pen) + 1e-6 * np.eye(X.shape[1])
    return np.linalg.solve(A, X.T @ y + pen * anchor)


def _usable(f: pd.DataFrame, cfg: ModelConfig, variant: str) -> pd.Series:
    ok = (f.played & f.raw_margin.notna() & f.margin.notna()
          & (f.games_home >= cfg.min_games) & (f.games_away >= cfg.min_games))
    if VARIANTS[variant] is not None:
        ok &= f[f"gap_d_{variant}"].notna()
    return ok


def fit(f: pd.DataFrame, cfg: ModelConfig = ModelConfig(), variant: str = "act") -> Fit:
    """Learn the weights from every usable game in `f`."""
    d = f[_usable(f, cfg, variant)]
    anchor_m = np.array([1.0, 0.0, 0.0, 0.0])
    anchor_t = np.array([1.0, 0.0, 0.0, 0.0])
    if len(d) < cfg.min_train:
        return Fit(anchor_m, anchor_t, 14.0, 18.5, len(d), variant)
    Xm, Xt = _design(d, MARGIN_FEATURES, variant), _design(d, TOTAL_FEATURES, variant)
    wm = _ridge(Xm, d.margin.to_numpy(float), cfg.ridge, anchor_m)
    wt = _ridge(Xt, d.total.to_numpy(float), cfg.ridge, anchor_t)
    return Fit(wm, wt, float(np.std(d.margin - Xm @ wm)), float(np.std(d.total - Xt @ wt)),
               len(d), variant)


def walk_forward(f: pd.DataFrame, cfg: ModelConfig = ModelConfig(), variant: str = "act",
                 refit_days: int = 7) -> pd.DataFrame:
    """Predict every game with weights learned only from earlier games.

    The weights are re-learned every `refit_days` days. Returns `f` plus pred_* columns and
    the chances (p_home and so on); games in the burn-in season are left blank.
    """
    f = f.sort_values(["date", "game_id"]).reset_index(drop=True)
    parts = []
    days = sorted(f.date.unique())
    current, last_fit = None, None
    for day in days:
        if last_fit is None or (day - last_fit).days >= refit_days:
            current = fit(f[f.date < day], cfg, variant)
            last_fit = day
        block = f[f.date == day]
        parts.append(current.predict(block))
    out = pd.concat([f, pd.concat(parts)], axis=1)
    out.loc[out.season <= cfg.burn_in_season, ["pred_margin", "pred_total", "pred_home",
                                               "pred_away", "sd_margin", "sd_total"]] = np.nan
    return add_chances(out)


def add_chances(p: pd.DataFrame) -> pd.DataFrame:
    """Win chance for the home team from the predicted margin and the size of past misses."""
    p = p.copy()
    p["p_home"] = [pricing.win_prob(m, s) if np.isfinite(m) and np.isfinite(s) else np.nan
                   for m, s in zip(p.pred_margin, p.sd_margin)]
    return p
