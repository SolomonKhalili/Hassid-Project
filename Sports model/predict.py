#!/usr/bin/env python3
"""
Today's NBA predictions: final score, margin, total and win chance for every game, next to
the sportsbook's line, with the bets where the model and the line disagree most.

    python3 predict.py                 # refresh data + injuries, predict today and tomorrow
    python3 predict.py --no-update     # predict from what's already downloaded
    python3 predict.py --quiet         # refresh and save only (used by the auto-update job)

Every run saves its predictions to the prediction_log table and writes PREDICTIONS.md, so
nothing is lost and every pick can be graded later against what happened.
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

import core
import data
import evaluate as ev
import injuries
import model
import players as players_mod
import pricing

HERE = Path(__file__).resolve().parent
NOT_LISTED_PLAY = 0.97     # chance a healthy, not-listed rotation player plays

LOG_SCHEMA = """CREATE TABLE IF NOT EXISTS prediction_log (
    game_id TEXT, made_at TEXT, game_date TEXT, home TEXT, away TEXT,
    pred_home REAL, pred_away REAL, pred_margin REAL, pred_total REAL, p_home REAL,
    sd_margin REAL, sd_total REAL, gap_home REAL, gap_away REAL,
    spread REAL, total REAL, home_ml INTEGER, away_ml INTEGER, book TEXT,
    PRIMARY KEY (game_id, made_at))"""


def live_chances(L: players_mod.Lineups, team: str, report: dict[str, dict]) -> tuple[dict, list]:
    """Each roster player's chance of playing tonight, from the injury report first and
    recent absences second. Returns (chances, notes)."""
    chances, notes = {}, []
    for pid in L.roster(team):
        r = report.get(pid)
        if r is not None:
            chances[pid] = r["play"]
        else:
            missed = L.missed(team, pid)
            chances[pid] = NOT_LISTED_PLAY if missed < 3 else players_mod.play_after_missing(missed)
    return chances, notes


def build(con, update: bool = True, days_ahead: int = 1):
    if update:
        data.update(con, quiet=True)
    games = core.games_table(con)
    plist = core.player_rows(con)
    cfg = model.ModelConfig()
    feats, rate, L = model.build_features(games, plist, cfg, return_state=True)
    fit = model.fit(feats, cfg, "act")

    today = datetime.now(data.ET).date()
    last = (today + timedelta(days=days_ahead)).isoformat()
    todo = feats[(feats.state == "pre") & (feats.game_date >= today.isoformat())
                 & (feats.game_date <= last)].copy()
    report, warnings = injuries.fetch(list(todo.game_id))
    injuries.save(con, today.isoformat(), report)

    outs = {}
    for i, g in todo.iterrows():
        for side in ("home", "away"):
            team = g[side]
            ch, _ = live_chances(L, team, report)
            res = L.gap(team, g.date, g.season, ch)
            todo.loc[i, f"gap_act_{side}"] = res["gap"]
            outs[(g.game_id, side)] = res["out"]
    todo = model.add_columns(todo)
    pred = fit.predict(todo)
    todo = model.add_chances(pd.concat([todo.drop(columns=[c for c in pred.columns if c in todo]), pred], axis=1))
    return todo, outs, report, warnings, fit, rate


def _bets_for(g) -> list[dict]:
    """Model chance and value for each side of the spread, total and moneyline."""
    out = []
    if pd.notna(g.spread_close):
        home = pricing.cover_prob(g.pred_margin, g.sd_margin, g.spread_close)
        for team, wpl, line, odds in ((g.home, home, g.spread_close, g.home_spread_odds_close),
                                      (g.away, pricing.flip(home), -g.spread_close, g.away_spread_odds_close)):
            odds = odds if pd.notna(odds) else -110
            out.append({"market": "Spread", "pick": f"{team} {line:+.1f}", "odds": odds,
                        "chance": wpl[0] / (wpl[0] + wpl[2]),
                        "ev": pricing.expected_value(wpl[0], wpl[2], odds),
                        "gap": abs(g.pred_margin + g.spread_close)})
    if pd.notna(g.total_close):
        over = pricing.over_prob(g.pred_total, g.sd_total, g.total_close)
        for side, wpl, odds in (("Over", over, g.over_odds_close), ("Under", pricing.flip(over), g.under_odds_close)):
            odds = odds if pd.notna(odds) else -110
            out.append({"market": "Total", "pick": f"{side} {g.total_close:.1f}", "odds": odds,
                        "chance": wpl[0] / (wpl[0] + wpl[2]),
                        "ev": pricing.expected_value(wpl[0], wpl[2], odds),
                        "gap": abs(g.pred_total - g.total_close)})
    if pd.notna(g.home_ml_close) and pd.notna(g.away_ml_close):
        for team, p, odds in ((g.home, g.p_home, g.home_ml_close), (g.away, 1 - g.p_home, g.away_ml_close)):
            out.append({"market": "Moneyline", "pick": f"{team} ML", "odds": odds, "chance": p,
                        "ev": pricing.expected_value(p, 1 - p, odds), "gap": np.nan})
    return out


def render(todo: pd.DataFrame, outs: dict, report: dict, warnings: list[str], fit) -> str:
    now = datetime.now(data.ET)
    L = [f"# NBA predictions", "",
         f"Made {now:%a %d %b %Y, %I:%M %p} ET from games through yesterday, today's injury "
         f"report ({len(report)} players listed) and DraftKings lines via ESPN.", ""]
    for w in warnings:
        L.append(f"> ⚠️ {w}")
    if warnings:
        L.append("")
    if todo.empty:
        return "\n".join(L + ["No games found for today or tomorrow."])
    picks = []
    for day, block in todo.sort_values("start_utc").groupby("game_date", sort=True):
        L.append(f"## {pd.Timestamp(day):%A %d %B}")
        L.append("")
        L.append("| Game (away @ home) | Predicted score | Margin | Total | Win chance | Fair ML | "
                 "DK spread | DK total | DK ML |")
        L.append("| --- | --- | ---: | ---: | --- | --- | ---: | ---: | --- |")
        for g in block.itertuples(index=False):
            tip = g.start_utc.tz_convert(data.ET)
            fav = g.home if g.pred_margin >= 0 else g.away
            win = g.p_home if g.pred_margin >= 0 else 1 - g.p_home
            ml = (f"{pricing.fmt_american(g.away_ml_close)} / {pricing.fmt_american(g.home_ml_close)}"
                  if pd.notna(g.home_ml_close) else "-")
            L.append(
                f"| {g.away} @ {g.home} ({tip:%-I:%M %p}) | {g.away} {g.pred_away:.0f} - {g.home} "
                f"{g.pred_home:.0f} | {fav} by {abs(g.pred_margin):.1f} | {g.pred_total:.1f} | "
                f"{fav} {win:.0%} | {fav} {pricing.fmt_american(pricing.fair_american(win))} | "
                f"{g.home} {g.spread_close:+.1f} | {g.total_close:.1f} | {ml} |"
                if pd.notna(g.spread_close) else
                f"| {g.away} @ {g.home} ({tip:%-I:%M %p}) | {g.away} {g.pred_away:.0f} - {g.home} "
                f"{g.pred_home:.0f} | {fav} by {abs(g.pred_margin):.1f} | {g.pred_total:.1f} | "
                f"{fav} {win:.0%} | {fav} {pricing.fmt_american(pricing.fair_american(win))} | "
                f"no line yet | - | - |")
            for b in _bets_for(g):
                picks.append({**b, "game": f"{g.away} @ {g.home}", "day": day})
        notes = []
        for g in block.itertuples(index=False):
            for side in ("away", "home"):
                o = outs.get((g.game_id, side)) or []
                if o:
                    who = ", ".join(f"{n} ({'out' if c == 0 else f'{c:.0%} to play'})" for n, _, c, _ in o)
                    pts = getattr(g, f"gap_act_{side}") * fit.margin_w[2]
                    change = ("about the same as" if abs(pts) < 0.5 else
                              f"{abs(pts):.1f} pts {'weaker' if pts < 0 else 'stronger'} than")
                    notes.append(f"- **{getattr(g, side)}** without {who}: tonight's lineup is "
                                 f"{change} the one in its recent games")
        if notes:
            L += ["", "Who's out (already in the numbers above). Players who have been out for "
                  "a while are already in the team's rating, so only fresh changes move the line:",
                  ""] + notes
        L.append("")
    best = sorted([p for p in picks if p["ev"] > 0], key=lambda p: -p["ev"])[:8]
    L.append("## Biggest disagreements with the line")
    L.append("")
    L.append("Chance and expected return are the model's own. Read the backtest before betting "
             "any of these: on past seasons the model did NOT beat DraftKings' closing line on "
             "its own (see BACKTEST.md).")
    L.append("")
    L.append("| Game | Bet | Price | Model chance | Break-even | Expected return |")
    L.append("| --- | --- | ---: | ---: | ---: | ---: |")
    for p in best:
        L.append(f"| {p['game']} | {p['market']}: {p['pick']} | {pricing.fmt_american(p['odds'])} | "
                 f"{p['chance']:.1%} | {pricing.breakeven(p['odds']):.1%} | {100 * p['ev']:+.1f}% |")
    if not best:
        L.append("| - | none | | | | |")
    L.append("")
    L.append(f"Typical miss: ±{fit.margin_sd:.1f} pts on the margin and ±{fit.total_sd:.1f} on the "
             f"total (one standard deviation), learned from {fit.n:,} past games.")
    return "\n".join(L)


def log(con, todo: pd.DataFrame) -> None:
    con.execute(LOG_SCHEMA)
    stamp = data.now_iso()
    for g in todo.itertuples(index=False):
        con.execute("INSERT OR REPLACE INTO prediction_log VALUES "
                    "(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (g.game_id, stamp, g.game_date, g.home, g.away, g.pred_home, g.pred_away,
                     g.pred_margin, g.pred_total, g.p_home, g.sd_margin, g.sd_total,
                     g.gap_act_home, g.gap_act_away,
                     None if pd.isna(g.spread_close) else g.spread_close,
                     None if pd.isna(g.total_close) else g.total_close,
                     None if pd.isna(g.home_ml_close) else int(g.home_ml_close),
                     None if pd.isna(g.away_ml_close) else int(g.away_ml_close), g.book_close))
    con.commit()


def main(argv: list[str]) -> None:
    con = data.connect()
    todo, outs, report, warnings, fit, _ = build(con, update="--no-update" not in argv)
    text = render(todo, outs, report, warnings, fit)
    (HERE / "PREDICTIONS.md").write_text(text + "\n")
    log(con, todo)
    if "--quiet" not in argv:
        print(text)


if __name__ == "__main__":
    main(sys.argv)
