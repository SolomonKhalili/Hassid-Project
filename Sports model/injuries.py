#!/usr/bin/env python3
"""
Tonight's injury report from ESPN, matched to players by ESPN's own player id.

Two feeds are merged (the same approach as the first-basket project):
  * each game's own page   - carries player ids, so matching is exact
  * the league-wide list   - catches anyone the game page missed (id read from the player link)
When the two disagree, the MORE SEVERE status wins: missing an injury costs more than a
false alarm.

Every report is also saved to the database (injury_log), because ESPN keeps no history -
saving it daily is the only way to later test "what did we know before the game?".
"""

from __future__ import annotations

import re
import sqlite3

import data

LEAGUE_FEED = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/injuries"

# Chance a player with this status plays tonight. ESPN only uses Out and Day-To-Day, plus
# a finer "fantasy" status. These are starting values; injury_log lets us measure them.
PLAY_CHANCE = {"out": 0.0, "ofs": 0.0, "suspension": 0.0, "doubtful": 0.10,
               "gtd": 0.50, "day-to-day": 0.50, "questionable": 0.50, "probable": 0.90}

SCHEMA = """CREATE TABLE IF NOT EXISTS injury_log (
    game_date TEXT, player_id TEXT, name TEXT, team TEXT, status TEXT, fantasy TEXT,
    detail TEXT, return_date TEXT, first_seen TEXT,
    PRIMARY KEY (game_date, player_id, status, fantasy))"""


def play_chance(status: str, fantasy: str = "") -> float:
    """0 = certain to sit, 1 = certain to play."""
    for key in (fantasy, status):
        k = (key or "").strip().lower()
        if k in PLAY_CHANCE:
            return PLAY_CHANCE[k]
    return 0.0 if "out" in (status or "").lower() else 0.5


def _row(p: dict, team: str, player_id: str | None) -> dict | None:
    ath = p.get("athlete") or {}
    if player_id is None:
        for link in ath.get("links") or []:
            m = re.search(r"/id/(\d+)", link.get("href", ""))
            if m:
                player_id = m[1]
                break
    if player_id is None:
        return None
    det = p.get("details") if isinstance(p.get("details"), dict) else {}
    what = " ".join(str(x) for x in (det.get("side"), det.get("type"), det.get("detail"))
                    if x and str(x).lower() not in ("not specified", "other"))
    return {"player_id": str(player_id), "name": ath.get("displayName") or ath.get("fullName") or "",
            "team": team, "status": p.get("status") or "",
            "fantasy": (det.get("fantasyStatus") or {}).get("abbreviation") or "",
            "detail": what or (p.get("shortComment") or "")[:90],
            "return_date": det.get("returnDate") or ""}


def fetch(game_ids: list[str]) -> tuple[dict[str, dict], list[str]]:
    """({player_id: row}, warnings). Each row has a 'play' chance between 0 and 1."""
    rows: dict[str, dict] = {}
    warnings: list[str] = []

    def take(r: dict | None) -> None:
        if not r:
            return
        r["play"] = play_chance(r["status"], r["fantasy"])
        old = rows.get(r["player_id"])
        if old is None or r["play"] < old["play"]:
            rows[r["player_id"]] = r

    n_game = 0
    for gid in game_ids:
        try:
            s = data.get_json(data.SUMMARY, {"event": gid})
            for blk in s.get("injuries") or []:
                team = (blk.get("team") or {}).get("abbreviation", "")
                for p in blk.get("injuries") or []:
                    take(_row(p, team, (p.get("athlete") or {}).get("id")))
                    n_game += 1
        except Exception as e:  # noqa: BLE001
            warnings.append(f"injury page for game {gid} failed: {e}")
    n_league = 0
    try:
        for t in data.get_json(LEAGUE_FEED).get("injuries") or []:
            for p in t.get("injuries") or []:
                team = ((p.get("athlete") or {}).get("team") or {}).get("abbreviation", "")
                take(_row(p, team, None))
                n_league += 1
    except Exception as e:  # noqa: BLE001
        warnings.append(f"league injury feed failed: {e}")
    if not rows:
        warnings.append("NO INJURY DATA LOADED - injuries are NOT accounted for in these predictions")
    elif n_game == 0 and game_ids:
        warnings.append("game injury pages returned nothing - using the league feed only")
    return rows, warnings


def save(con: sqlite3.Connection, game_date: str, rows: dict[str, dict]) -> int:
    """Keep today's report. One row per player per status: a later change adds its own row."""
    con.execute(SCHEMA)
    before = con.total_changes
    stamp = data.now_iso()
    for r in rows.values():
        con.execute("INSERT OR IGNORE INTO injury_log VALUES (?,?,?,?,?,?,?,?,?)",
                    (game_date, r["player_id"], r["name"], r["team"], r["status"], r["fantasy"],
                     r["detail"], r["return_date"], stamp))
    con.commit()
    return con.total_changes - before


if __name__ == "__main__":
    con = data.connect()
    ids = [g for (g,) in con.execute(
        "SELECT game_id FROM games WHERE state='pre' ORDER BY start_utc LIMIT 15")]
    report, warns = fetch(ids)
    for w in warns:
        print("!", w)
    for r in sorted(report.values(), key=lambda r: (r["team"], r["play"])):
        print(f"{r['team']:5s} {r['name']:26s} {r['status']:11s} {r['fantasy']:4s} "
              f"play {r['play']:.0%}  {r['detail']}")
