#!/usr/bin/env python3
"""
Loads the database into tables the model works on.

    games_table(con)    one row per game: teams, scores, possessions, rest, lines
    team_rows(games)    two rows per game (one per team) for rating fits
    player_rows(con)    one row per player per game
"""

from __future__ import annotations

import sqlite3

import numpy as np
import pandas as pd

import data

REG_MINUTES = 48.0
OT_MINUTES = 5.0


def games_table(con: sqlite3.Connection, include_unplayed: bool = True) -> pd.DataFrame:
    """One row per game, oldest first, with both teams' box scores, possessions,
    rest days and the sportsbook's opening and closing lines."""
    g = pd.read_sql_query("SELECT * FROM games WHERE state != 'off'", con)
    if not include_unplayed:
        g = g[g.state == "post"]
    g["date"] = pd.to_datetime(g.game_date)
    g["start_utc"] = pd.to_datetime(g.start_utc, utc=True)
    g["played"] = (g.state == "post") & g.home_score.notna()

    box = pd.read_sql_query("SELECT * FROM team_box", con)
    stat_cols = [c for c in box.columns if c not in ("game_id", "team")]
    for side in ("home", "away"):
        b = box.rename(columns={c: f"{side}_{c}" for c in stat_cols})
        g = g.merge(b, how="left", left_on=["game_id", side], right_on=["game_id", "team"])
        g = g.drop(columns="team")

    # Possessions: each team's trips = shots + turnovers + trips to the line - second chances.
    # The two teams have (almost) the same number, so the game's count is their average.
    for side in ("home", "away"):
        g[f"{side}_poss_raw"] = (g[f"{side}_fga"] + 0.44 * g[f"{side}_fta"]
                                 - g[f"{side}_oreb"] + g[f"{side}_tov"])
    g["poss"] = (g.home_poss_raw + g.away_poss_raw) / 2
    g["minutes"] = REG_MINUTES + OT_MINUTES * (g.periods.fillna(4) - 4).clip(lower=0)
    g["pace"] = g.poss * REG_MINUTES / g.minutes          # possessions per 48 minutes
    g["home_eff"] = 100 * g.home_score / g.poss           # points per 100 possessions
    g["away_eff"] = 100 * g.away_score / g.poss
    g["margin"] = g.home_score - g.away_score
    g["total"] = g.home_score + g.away_score
    g["ot"] = (g.periods.fillna(4) > 4).astype(int)

    lines = pd.DataFrame.from_dict(data.load_lines(con), orient="index")
    if len(lines):
        lines.index.name = "game_id"
        g = g.merge(lines.reset_index(), how="left", on="game_id")

    g = g.sort_values(["start_utc", "game_id"]).reset_index(drop=True)
    return _add_rest(g)


def _add_rest(g: pd.DataFrame) -> pd.DataFrame:
    """Days since each team's previous game (this season), and games in the last 4 and 7 days."""
    last: dict[tuple, list] = {}
    cols = {f"{s}_{k}": [] for s in ("home", "away") for k in ("rest", "g4", "g7", "prev_away")}
    for row in g.itertuples(index=False):
        for side in ("home", "away"):
            team = getattr(row, side)
            hist = last.setdefault((row.season, team), [])
            d = row.date
            cols[f"{side}_rest"].append((d - hist[-1][0]).days if hist else np.nan)
            cols[f"{side}_g4"].append(sum(1 for (x, _) in hist if 0 < (d - x).days <= 3))
            cols[f"{side}_g7"].append(sum(1 for (x, _) in hist if 0 < (d - x).days <= 6))
            cols[f"{side}_prev_away"].append(hist[-1][1] if hist else np.nan)
        for side in ("home", "away"):
            last[(row.season, getattr(row, side))].append((row.date, int(side == "away")))
    for k, v in cols.items():
        g[k] = v
    for side in ("home", "away"):
        g[f"{side}_b2b"] = (g[f"{side}_rest"] == 1).astype(int)     # played yesterday
    return g


def team_rows(games: pd.DataFrame) -> pd.DataFrame:
    """Two rows per played game: each team's offence against the other's defence."""
    g = games[games.played & games.poss.notna()]
    parts = []
    for side, opp in (("home", "away"), ("away", "home")):
        parts.append(pd.DataFrame({
            "game_id": g.game_id, "date": g.date, "season": g.season,
            "team": g[side], "opp": g[opp],
            "is_home": float(side == "home") * (1 - g.neutral),
            "is_away": float(side == "away") * (1 - g.neutral),
            "pts": g[f"{side}_score"], "poss": g.poss, "pace": g.pace,
            "eff": g[f"{side}_eff"],
            "fgm": g[f"{side}_fgm"], "fga": g[f"{side}_fga"],
            "fg3m": g[f"{side}_fg3m"], "fg3a": g[f"{side}_fg3a"],
            "ftm": g[f"{side}_ftm"], "fta": g[f"{side}_fta"],
            "oreb": g[f"{side}_oreb"], "dreb": g[f"{side}_dreb"], "tov": g[f"{side}_tov"],
            "opp_dreb": g[f"{opp}_dreb"],
        }))
    return pd.concat(parts, ignore_index=True).sort_values(["date", "game_id"]).reset_index(drop=True)


def player_rows(con: sqlite3.Connection) -> pd.DataFrame:
    """One row per player per played game, with the game's date and season."""
    p = pd.read_sql_query("""
        SELECT p.*, g.game_date, g.season, g.season_type, g.start_utc
        FROM players p JOIN games g USING(game_id) WHERE g.state='post'""", con)
    p["date"] = pd.to_datetime(p.game_date)
    num = ["minutes", "pts", "fgm", "fga", "fg3m", "fg3a", "ftm", "fta", "oreb", "dreb",
           "ast", "stl", "blk", "tov", "pf", "plus_minus"]
    p[num] = p[num].fillna(0)
    return p.sort_values(["start_utc", "game_id"]).reset_index(drop=True)
