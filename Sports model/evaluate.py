#!/usr/bin/env python3
"""
Scores a table of predictions against what happened and against the sportsbook's lines.

It answers four questions, in this order:
  1. How close are the predictions, next to the sportsbook's own numbers?
  2. Does the model know anything the line doesn't?  (the weight test)
  3. Would betting the disagreements have made money, and did the line move our way?
  4. When the model says 60%, does it happen 60% of the time?  (calibration)

Used by backtest.py. Every function takes the walk-forward predictions table: one row per
game with the prediction made BEFORE that game, the result, and the lines.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

import pricing

DEFAULT_PRICE = -110


def _rmse(x) -> float:
    x = np.asarray(x, dtype=float)
    return float(np.sqrt(np.mean(x ** 2))) if len(x) else float("nan")


def _mae(x) -> float:
    x = np.asarray(x, dtype=float)
    return float(np.mean(np.abs(x))) if len(x) else float("nan")


def market_win_prob(df: pd.DataFrame, when: str = "close") -> pd.Series:
    """The line's fair chance that the home team wins (sportsbook's cut removed)."""
    out = []
    for h, a in zip(df[f"home_ml_{when}"], df[f"away_ml_{when}"]):
        out.append(pricing.devig(h, a)[0] if pd.notna(h) and pd.notna(a) and h != 0 and a != 0
                   else np.nan)
    return pd.Series(out, index=df.index)


# ----------------------------------------------------------------------
# 1. Accuracy
# ----------------------------------------------------------------------

def accuracy(df: pd.DataFrame, by: str = "season") -> pd.DataFrame:
    """Average miss (MAE) and RMSE for margin and total: model, closing line, opening line.
    Only games that have both a prediction and a closing line are counted, so the three
    are compared on exactly the same games."""
    d = df[df.pred_margin.notna() & df.spread_close.notna() & df.total_close.notna()].copy()
    d["p_mkt"] = market_win_prob(d)
    rows = []
    groups = list(d.groupby(by)) + [("all", d)]
    for key, g in groups:
        has_open = g.spread_open.notna() & g.total_open.notna()
        pm = g.p_mkt.notna() & g.p_home.notna()
        won = (g.margin > 0).astype(float)
        eps = 1e-9

        def logloss(p):
            p = np.clip(p[pm], eps, 1 - eps)
            return float(-np.mean(won[pm] * np.log(p) + (1 - won[pm]) * np.log(1 - p)))

        rows.append({
            by: key, "games": len(g),
            "margin_mae_model": _mae(g.margin - g.pred_margin),
            "margin_mae_close": _mae(g.margin + g.spread_close),
            "margin_mae_open": _mae((g.margin + g.spread_open)[has_open]),
            "margin_rmse_model": _rmse(g.margin - g.pred_margin),
            "margin_rmse_close": _rmse(g.margin + g.spread_close),
            "total_mae_model": _mae(g.total - g.pred_total),
            "total_mae_close": _mae(g.total - g.total_close),
            "total_mae_open": _mae((g.total - g.total_open)[has_open]),
            "total_rmse_model": _rmse(g.total - g.pred_total),
            "total_rmse_close": _rmse(g.total - g.total_close),
            "winner_model": float(np.mean((g.pred_margin > 0) == (g.margin > 0))),
            "winner_close": float(np.mean(((-g.spread_close) > 0)[g.spread_close != 0]
                                          == (g.margin > 0)[g.spread_close != 0])),
            "logloss_model": logloss(g.p_home),
            "logloss_close": logloss(g.p_mkt),
            "brier_model": float(np.mean((g.p_home[pm] - won[pm]) ** 2)),
            "brier_close": float(np.mean((g.p_mkt[pm] - won[pm]) ** 2)),
            "bias_margin": float(np.mean(g.pred_margin - g.margin)),
            "bias_total": float(np.mean(g.pred_total - g.total)),
        })
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------
# 2. Does the model know anything the line doesn't?
# ----------------------------------------------------------------------

def weight_test(df: pd.DataFrame, what: str = "margin", when: str = "close") -> dict:
    """Best blend of model and line:  result = line + w x (model - line).

    w = 0  the model adds nothing to the line.      w = 1  the model beats it outright.
    Reported with a standard error; w is only real if it is clearly above zero
    (about 2 standard errors).
    """
    if what == "margin":
        line = -df[f"spread_{when}"]
        model, actual = df.pred_margin, df.margin
    else:
        line = df[f"total_{when}"]
        model, actual = df.pred_total, df.total
    ok = line.notna() & model.notna() & actual.notna()
    x = (model - line)[ok].to_numpy(float)
    y = (actual - line)[ok].to_numpy(float)
    if len(x) < 30 or np.sum(x * x) == 0:
        return {"what": what, "when": when, "n": int(len(x)), "w": float("nan"), "se": float("nan")}
    w = float(np.sum(x * y) / np.sum(x * x))
    resid = y - w * x
    se = float(math.sqrt(np.sum(resid ** 2) / (len(x) - 1) / np.sum(x * x)))
    return {"what": what, "when": when, "n": int(len(x)), "w": w, "se": se,
            "t": w / se if se > 0 else float("nan"),
            "avg_gap": float(np.mean(np.abs(x)))}


# ----------------------------------------------------------------------
# 3. Betting the disagreements
# ----------------------------------------------------------------------

def _settle(win: np.ndarray, push: np.ndarray, odds: np.ndarray) -> np.ndarray:
    pay = np.where(odds < 0, 100 / -odds, odds / 100)
    return np.where(push, 0.0, np.where(win, pay, -1.0))


def bets(df: pd.DataFrame, what: str = "spread", when: str = "close",
         gap_col: str | None = None) -> pd.DataFrame:
    """Every game as a 1-unit bet on the side the model prefers, at the line named.

    Returns one row per bet with: gap (how far the model is from the line, in points, always
    positive), result, profit, and clv (how far the closing line ended up on our side of the
    line we took - only meaningful when betting the opener).
    """
    if what == "spread":
        line, close = df[f"spread_{when}"], df.spread_close
        gap = df[gap_col] if gap_col else df.pred_margin + line     # + means model likes home
        side_home = gap > 0
        diff = df.margin + line                                      # + means home covered
        win = np.where(side_home, diff > 0, diff < 0)
        push = diff == 0
        odds = np.where(side_home, df[f"home_spread_odds_{when}"], df[f"away_spread_odds_{when}"])
        clv = np.where(side_home, line - close, close - line)
        label = np.where(side_home, df.home, df.away)
    elif what == "total":
        line, close = df[f"total_{when}"], df.total_close
        gap = df[gap_col] if gap_col else df.pred_total - line       # + means model likes over
        side_over = gap > 0
        diff = df.total - line
        win = np.where(side_over, diff > 0, diff < 0)
        push = diff == 0
        odds = np.where(side_over, df[f"over_odds_{when}"], df[f"under_odds_{when}"])
        clv = np.where(side_over, close - line, line - close)
        label = np.where(side_over, "over", "under")
    else:
        raise ValueError(what)
    odds = pd.to_numeric(pd.Series(odds, index=df.index), errors="coerce").fillna(DEFAULT_PRICE)
    odds = odds.where(odds.abs() >= 100, DEFAULT_PRICE).to_numpy(float)
    out = pd.DataFrame({
        "game_id": df.game_id, "date": df.date, "season": df.season, "pick": label,
        "line": line, "gap": np.abs(gap), "odds": odds,
        "win": win, "push": push, "profit": _settle(np.asarray(win), np.asarray(push), odds),
        "clv": clv,
    })
    ok = line.notna() & gap.notna() & df.margin.notna() & (gap != 0)
    return out[ok].reset_index(drop=True)


def bet_summary(b: pd.DataFrame, cuts=(0, 1, 2, 3, 4, 6)) -> pd.DataFrame:
    """Record and return by how far the model disagreed with the line."""
    rows = []
    for lo in cuts:
        s = b[b.gap >= lo]
        decided = s[~s.push]
        n = len(decided)
        if n == 0:
            continue
        wins = int(decided.win.sum())
        rate = wins / n
        roi = float(s.profit.mean())
        rows.append({
            "gap": f"{lo}+ pts", "bets": len(s), "won": wins, "lost": n - wins,
            "pushed": int(s.push.sum()), "win_pct": rate,
            "win_pct_se": math.sqrt(rate * (1 - rate) / n),
            "roi": roi, "roi_se": float(s.profit.std(ddof=1) / math.sqrt(len(s))) if len(s) > 1 else float("nan"),
            "avg_clv": float(s.clv.mean()),
            "clv_beat_pct": float((s.clv > 0).mean()), "clv_lost_pct": float((s.clv < 0).mean()),
        })
    return pd.DataFrame(rows)


def moneyline_bets(df: pd.DataFrame, when: str = "close", min_edge: float = 0.0,
                   prob_col: str = "p_home") -> pd.DataFrame:
    """A 1-unit moneyline bet whenever the model's chance beats the price's break-even by
    at least `min_edge` (0.02 = 2 points)."""
    rows = []
    for r in df.itertuples(index=False):
        h, a = getattr(r, f"home_ml_{when}"), getattr(r, f"away_ml_{when}")
        p = getattr(r, prob_col)
        if pd.isna(h) or pd.isna(a) or pd.isna(p) or pd.isna(r.margin) or abs(h) < 100 or abs(a) < 100:
            continue
        for team, prob, odds, won in ((r.home, p, h, r.margin > 0), (r.away, 1 - p, a, r.margin < 0)):
            edge = prob - pricing.breakeven(odds)
            if edge >= min_edge and edge > 0:
                rows.append({"game_id": r.game_id, "date": r.date, "season": r.season,
                             "pick": team, "odds": odds, "edge": edge, "win": bool(won),
                             "profit": pricing.payout(odds) if won else -1.0})
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------
# 4. Calibration
# ----------------------------------------------------------------------

def calibration(prob: pd.Series, happened: pd.Series,
                edges=(0.0, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 1.0001)) -> pd.DataFrame:
    """For each band of predicted chance: how often it actually happened."""
    ok = prob.notna() & happened.notna()
    p, y = prob[ok].to_numpy(float), happened[ok].to_numpy(float)
    rows = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (p >= lo) & (p < hi)
        if m.sum() == 0:
            continue
        rate = float(y[m].mean())
        rows.append({"said": f"{lo:.0%}-{min(hi, 1):.0%}", "games": int(m.sum()),
                     "avg_said": float(p[m].mean()), "happened": rate,
                     "se": math.sqrt(max(rate * (1 - rate), 1e-9) / m.sum())})
    return pd.DataFrame(rows)


def wilson(wins: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% range for the true win rate behind a record."""
    if n == 0:
        return 0.0, 1.0
    p = wins / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return centre - half, centre + half
