#!/usr/bin/env python3
"""
Replays past seasons: every game is predicted using only what was known before it, then
scored against the result and against the sportsbook's own lines.

    python3 backtest.py            # full report (about a minute)
    python3 backtest.py --save     # also writes BACKTEST.md

How to read it
  * 2023-24 only warms the ratings up. Settings were chosen on games through June 2025.
    2025-26 and 2026-27 are untouched test seasons - judge the model on those.
  * "Lineups known" uses who actually played. That is fair against the CLOSING line (lineups
    are public before tip-off) but NOT against the opening line.
  * "Day before" guesses absences from recent games only. That is the fair test against the
    OPENING line.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

import core
import data
import evaluate as ev
import model

HERE = Path(__file__).resolve().parent
SEASON_NAME = {2024: "2023-24", 2025: "2024-25", 2026: "2025-26", 2027: "2026-27"}


def run(cfg: model.ModelConfig = model.ModelConfig(), con=None) -> dict[str, pd.DataFrame]:
    """Walk-forward predictions for each view of who is playing: {'act': table, 'exp': ...}."""
    con = con or data.connect()
    games = core.games_table(con)
    games = games[games.played].reset_index(drop=True)
    feats = model.build_features(games, core.player_rows(con), cfg)
    return {v: model.walk_forward(feats, cfg, v) for v in model.VARIANTS}


def _scored(p: pd.DataFrame, cfg: model.ModelConfig) -> pd.DataFrame:
    return p[p.pred_margin.notna() & (p.season > cfg.burn_in_season)]


def _pct(x: float) -> str:
    return f"{100 * x:.1f}%"


def report(preds: dict[str, pd.DataFrame], cfg: model.ModelConfig = model.ModelConfig()) -> str:
    L: list[str] = []
    act, exp, none = (_scored(preds[v], cfg) for v in ("act", "exp", "none"))

    L.append("# Backtest\n")
    L.append(f"{len(act):,} games scored, {act.date.min():%d %b %Y} to {act.date.max():%d %b %Y}. "
             "Every prediction used only earlier games.\n")

    # ---- 1. accuracy ----
    L.append("## 1. How close are the predictions?\n")
    L.append("Average miss in points (lower is better). 'Line' is the sportsbook's closing number.\n")
    L.append("| Season | Games | Margin: model | Margin: line | Total: model | Total: line | "
             "Winner: model | Winner: line |")
    L.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    acc = ev.accuracy(act)
    for r in acc.itertuples(index=False):
        name = SEASON_NAME.get(r.season, "All")
        L.append(f"| {name} | {r.games:,} | {r.margin_mae_model:.2f} | {r.margin_mae_close:.2f} | "
                 f"{r.total_mae_model:.2f} | {r.total_mae_close:.2f} | "
                 f"{_pct(r.winner_model)} | {_pct(r.winner_close)} |")
    L.append("")
    L.append("What each layer adds (all scored seasons, average miss):\n")
    L.append("| Version | Margin | Total |")
    L.append("| --- | ---: | ---: |")
    for label, d in (("Team ratings only", none), ("+ absences guessed the day before", exp),
                     ("+ lineups known", act)):
        a = ev.accuracy(d).iloc[-1]
        L.append(f"| {label} | {a.margin_mae_model:.2f} | {a.total_mae_model:.2f} |")
    a = acc.iloc[-1]
    L.append(f"| Sportsbook closing line | {a.margin_mae_close:.2f} | {a.total_mae_close:.2f} |")
    L.append(f"| Sportsbook opening line | {a.margin_mae_open:.2f} | {a.total_mae_open:.2f} |")
    L.append("")
    L.append(f"Win chances (lower is better): model log-loss {a.logloss_model:.4f} vs line "
             f"{a.logloss_close:.4f}; Brier {a.brier_model:.4f} vs {a.brier_close:.4f}.\n")

    # ---- 2. weight test ----
    L.append("## 2. Does the model know anything the line doesn't?\n")
    L.append("Best blend = line + w x (model - line). w = 0 means the model adds nothing; "
             "w is only real if it is about 2 standard errors above zero.\n")
    L.append("| Test | Games | w | Std. error | Verdict |")
    L.append("| --- | ---: | ---: | ---: | --- |")
    tests = [("Margin vs closing line (lineups known)", act, "margin", "close"),
             ("Total vs closing line (lineups known)", act, "total", "close"),
             ("Margin vs opening line (day before)", exp, "margin", "open"),
             ("Total vs opening line (day before)", exp, "total", "open")]
    for label, d, what, when in tests:
        w = ev.weight_test(d, what, when)
        verdict = ("adds information" if w["w"] - 2 * w["se"] > 0 else
                   "nothing proven" if w["w"] + 2 * w["se"] > 0 else "worse than the line alone")
        L.append(f"| {label} | {w['n']:,} | {w['w']:+.2f} | {w['se']:.2f} | {verdict} |")
    L.append("")

    # ---- 3. betting ----
    L.append("## 3. Betting the disagreements\n")
    L.append("One unit on the model's side at the price stored for that line. Break-even at "
             "-110 is 52.4%. 'Line moved our way' is the average number of points the closing "
             "line ended up on our side of the opening line we took.\n")
    for label, d, what, when in (
            ("Spreads at the OPENING line (day-before model)", exp, "spread", "open"),
            ("Totals at the OPENING line (day-before model)", exp, "total", "open"),
            ("Spreads at the CLOSING line (lineups known)", act, "spread", "close"),
            ("Totals at the CLOSING line (lineups known)", act, "total", "close")):
        L.append(f"**{label}**\n")
        L.append("| Model vs line | Bets | Record | Win % | Return per bet | Line moved our way |")
        L.append("| --- | ---: | --- | ---: | ---: | ---: |")
        for r in ev.bet_summary(ev.bets(d, what, when)).itertuples(index=False):
            clv = f"{r.avg_clv:+.2f}" if when == "open" else "-"
            L.append(f"| {r.gap} | {r.bets:,} | {r.won}-{r.lost}-{r.pushed} | "
                     f"{_pct(r.win_pct)} ± {100 * 1.96 * r.win_pct_se:.1f} | "
                     f"{100 * r.roi:+.1f}% ± {100 * 1.96 * r.roi_se:.1f} | {clv} |")
        L.append("")
    ml = ev.moneyline_bets(act, "close", 0.03)
    if len(ml):
        L.append(f"Moneylines at the closing price when the model's chance beat the break-even by "
                 f"3+ points: {len(ml):,} bets, {int(ml.win.sum())} won, return per bet "
                 f"{100 * ml.profit.mean():+.1f}% ± "
                 f"{100 * 1.96 * ml.profit.std(ddof=1) / np.sqrt(len(ml)):.1f}.\n")

    # ---- 4. calibration ----
    L.append("## 4. When the model says 60%, does it happen 60% of the time?\n")
    L.append("| Model said home wins | Games | Average said | Home actually won |")
    L.append("| --- | ---: | ---: | ---: |")
    for r in ev.calibration(act.p_home, (act.margin > 0).astype(float)).itertuples(index=False):
        L.append(f"| {r.said} | {r.games:,} | {_pct(r.avg_said)} | {_pct(r.happened)} ± "
                 f"{100 * 1.96 * r.se:.1f} |")
    L.append("")
    miss_m = (act.margin - act.pred_margin)
    miss_t = (act.total - act.pred_total)
    L.append(f"Spread of misses: margin {miss_m.std():.1f} points (the model assumed "
             f"{act.sd_margin.mean():.1f}), total {miss_t.std():.1f} (assumed {act.sd_total.mean():.1f}). "
             f"Average lean: margin {miss_m.mean():+.2f}, total {miss_t.mean():+.2f}.\n")
    return "\n".join(L)


def main(argv: list[str]) -> None:
    cfg = model.ModelConfig()
    preds = run(cfg)
    text = report(preds, cfg)
    print(text)
    if "--save" in argv:
        (HERE / "BACKTEST.md").write_text(text + "\n")
        print(f"\nSaved to {HERE / 'BACKTEST.md'}")


if __name__ == "__main__":
    main(sys.argv)
