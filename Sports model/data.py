#!/usr/bin/env python3
"""
Download NBA games, box scores and sportsbook lines from ESPN's free public feeds
into nba_model.db (SQLite).

    python3 data.py backfill            # every season from 2023-24 to today (~4 min the first time)
    python3 data.py update              # only what's new or not finished yet (seconds)
    python3 data.py status              # what's in the database

Sources (no key, no account):
  * scoreboard   site.api.espn.com/.../scoreboard?dates=YYYYMMDD   - schedule, scores, quarters, status
  * summary      site.api.espn.com/.../summary?event=ID            - team + player box score, referees
  * odds         sports.core.api.espn.com/.../competitions/ID/odds - OPENING and CLOSING
                                                                     moneyline, spread and total

Which sportsbook the lines are from depends on the season, because ESPN changed partner:
2023-24 several books (DraftKings among them), 2024-25 ESPN BET only, Dec 2025 onward DraftKings.
Every book ESPN lists is stored; load_lines() picks one per game (DraftKings first).

For a game that hasn't started, the "close" columns hold the current price. They are refreshed
on every update, and each change is also appended to line_history.
"""

from __future__ import annotations

import sqlite3
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

HERE = Path(__file__).resolve().parent
DB = HERE / "nba_model.db"
ET = ZoneInfo("America/New_York")

SCOREBOARD = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"
SUMMARY = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary"
ODDS = ("https://sports.core.api.espn.com/v2/sports/basketball/leagues/nba/events/{g}"
        "/competitions/{g}/odds")

# ESPN season year = the year the season ENDS (2024 = 2023-24).
FIRST_SEASON = 2024
# Season types kept: 2 regular season (incl. NBA Cup), 3 playoffs, 5 play-in.
KEEP_TYPES = {2, 3, 5}
# ESPN's codes for the 30 teams. Anything else (All-Star teams, Rising Stars) is skipped.
NBA_TEAMS = frozenset("""ATL BOS BKN CHA CHI CLE DAL DEN DET GS HOU IND LAC LAL MEM MIA MIL MIN
                         NO NY OKC ORL PHI PHX POR SAC SA TOR UTAH WSH""".split())
# Which book to trust first when ESPN lists several for one game.
BOOK_ORDER = ["DraftKings", "ESPN BET", "Caesars Sportsbook (New Jersey)", "MGM"]

SESSION = requests.Session()
SESSION.headers["User-Agent"] = "Mozilla/5.0 (sports-model)"


def get_json(url: str, params: dict | None = None, tries: int = 4) -> dict:
    for i in range(tries):
        try:
            r = SESSION.get(url, params=params, timeout=25)
            if r.status_code == 404:
                return {}
            r.raise_for_status()
            return r.json()
        except (requests.RequestException, ValueError):
            if i == tries - 1:
                raise
            time.sleep(1.5 * (i + 1))
    return {}


# ----------------------------------------------------------------------
# Database
# ----------------------------------------------------------------------

SCHEMA = """
CREATE TABLE IF NOT EXISTS games (
    game_id TEXT PRIMARY KEY,
    game_date TEXT,          -- Eastern date, YYYY-MM-DD
    start_utc TEXT,
    season INTEGER,          -- ESPN year: 2026 = 2025-26
    season_type INTEGER,     -- 2 regular, 3 playoffs, 5 play-in
    home TEXT, away TEXT,
    home_score INTEGER, away_score INTEGER,      -- final, overtime included
    home_reg INTEGER, away_reg INTEGER,          -- after 4 quarters
    periods INTEGER,                             -- 4 = no overtime, 5 = one overtime...
    state TEXT,              -- pre / in / post (played to a finish) / off (postponed, cancelled)
    neutral INTEGER DEFAULT 0,
    officials TEXT,
    detail_done INTEGER DEFAULT 0,   -- box score + lines stored for the final game
    updated_at TEXT
);
CREATE TABLE IF NOT EXISTS team_box (
    game_id TEXT, team TEXT,
    fgm INTEGER, fga INTEGER, fg3m INTEGER, fg3a INTEGER, ftm INTEGER, fta INTEGER,
    oreb INTEGER, dreb INTEGER, ast INTEGER, stl INTEGER, blk INTEGER, tov INTEGER, pf INTEGER,
    pts_paint INTEGER, pts_fastbreak INTEGER, pts_off_tov INTEGER,
    PRIMARY KEY (game_id, team)
);
CREATE TABLE IF NOT EXISTS players (
    game_id TEXT, team TEXT, player_id TEXT, name TEXT, position TEXT,
    starter INTEGER, dnp INTEGER, reason TEXT, minutes REAL,
    pts INTEGER, fgm INTEGER, fga INTEGER, fg3m INTEGER, fg3a INTEGER, ftm INTEGER, fta INTEGER,
    oreb INTEGER, dreb INTEGER, ast INTEGER, stl INTEGER, blk INTEGER, tov INTEGER, pf INTEGER,
    plus_minus INTEGER,
    PRIMARY KEY (game_id, player_id)
);
CREATE TABLE IF NOT EXISTS odds (
    game_id TEXT, provider TEXT,
    spread_open REAL, spread_close REAL,          -- HOME team's spread (negative = home favoured)
    home_spread_odds_open INTEGER, away_spread_odds_open INTEGER,
    home_spread_odds_close INTEGER, away_spread_odds_close INTEGER,
    total_open REAL, total_close REAL,
    over_odds_open INTEGER, under_odds_open INTEGER,
    over_odds_close INTEGER, under_odds_close INTEGER,
    home_ml_open INTEGER, away_ml_open INTEGER,
    home_ml_close INTEGER, away_ml_close INTEGER,
    is_final INTEGER,        -- 1 = the game had started, so "close" is the real closing line
    fetched_at TEXT,
    PRIMARY KEY (game_id, provider)
);
CREATE TABLE IF NOT EXISTS line_history (       -- every change we saw before tip-off
    game_id TEXT, provider TEXT, seen_at TEXT,
    spread REAL, home_spread_odds INTEGER, away_spread_odds INTEGER,
    total REAL, over_odds INTEGER, under_odds INTEGER,
    home_ml INTEGER, away_ml INTEGER,
    PRIMARY KEY (game_id, provider, seen_at)
);
CREATE TABLE IF NOT EXISTS days_done (game_date TEXT PRIMARY KEY);
"""


def connect(path: Path | str = DB) -> sqlite3.Connection:
    con = sqlite3.connect(path, timeout=30)
    con.executescript(SCHEMA)
    return con


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ----------------------------------------------------------------------
# Parsing
# ----------------------------------------------------------------------

def _int(x):
    try:
        return int(float(str(x).replace("+", "")))
    except (TypeError, ValueError):
        return None


def _float(x):
    try:
        return float(str(x).replace("+", ""))
    except (TypeError, ValueError):
        return None


def _made_att(text) -> tuple[int | None, int | None]:
    try:
        m, a = str(text).split("-")
        return int(m), int(a)
    except ValueError:
        return None, None


def game_state(status_type: dict) -> str:
    """pre / in / post / off.  'post' only when the game was actually played to a finish -
    ESPN also files postponed and cancelled games under 'post', with a 0-0 score."""
    state = status_type.get("state", "pre")
    name = status_type.get("name", "")
    if state == "post":
        return "post" if name == "STATUS_FINAL" or status_type.get("completed") else "off"
    if name in ("STATUS_POSTPONED", "STATUS_CANCELED", "STATUS_SUSPENDED"):
        return "off"
    return state


def parse_scoreboard(data: dict) -> list[dict]:
    out = []
    for ev in data.get("events", []):
        season = ev.get("season", {})
        stype = season.get("type")
        if stype not in KEEP_TYPES:
            continue
        comp = ev["competitions"][0]
        teams = {c["homeAway"]: c for c in comp["competitors"]}
        if "home" not in teams or "away" not in teams:
            continue
        home, away = (teams[s]["team"].get("abbreviation") for s in ("home", "away"))
        if home not in NBA_TEAMS or away not in NBA_TEAMS:
            continue
        start = datetime.fromisoformat(ev["date"].replace("Z", "+00:00"))
        state = game_state(comp["status"]["type"])
        played = state == "post"

        def score(c):
            return _int(c.get("score")) if played else None

        def regulation(c):
            q = [_int(l.get("value")) for l in c.get("linescores", [])]
            return sum(q[:4]) if played and len(q) >= 4 and None not in q[:4] else None

        periods = max(len(teams["home"].get("linescores", [])), comp["status"].get("period") or 0)
        out.append({
            "game_id": ev["id"],
            "game_date": start.astimezone(ET).date().isoformat(),
            "start_utc": start.isoformat(),
            "season": season.get("year"),
            "season_type": stype,
            "home": home, "away": away,
            "home_score": score(teams["home"]), "away_score": score(teams["away"]),
            "home_reg": regulation(teams["home"]), "away_reg": regulation(teams["away"]),
            "periods": periods if played else None,
            "state": state,
            "neutral": int(bool(comp.get("neutralSite"))),
        })
    return out


def parse_team_box(summary: dict) -> list[dict]:
    rows = []
    for tm in summary.get("boxscore", {}).get("teams", []):
        st = {s["name"]: s.get("displayValue") for s in tm.get("statistics", [])}
        fgm, fga = _made_att(st.get("fieldGoalsMade-fieldGoalsAttempted"))
        f3m, f3a = _made_att(st.get("threePointFieldGoalsMade-threePointFieldGoalsAttempted"))
        ftm, fta = _made_att(st.get("freeThrowsMade-freeThrowsAttempted"))
        rows.append({
            "team": tm["team"]["abbreviation"],
            "fgm": fgm, "fga": fga, "fg3m": f3m, "fg3a": f3a, "ftm": ftm, "fta": fta,
            "oreb": _int(st.get("offensiveRebounds")), "dreb": _int(st.get("defensiveRebounds")),
            "ast": _int(st.get("assists")), "stl": _int(st.get("steals")),
            "blk": _int(st.get("blocks")),
            "tov": _int(st.get("totalTurnovers", st.get("turnovers"))),
            "pf": _int(st.get("fouls")),
            "pts_paint": _int(st.get("pointsInPaint")),
            "pts_fastbreak": _int(st.get("fastBreakPoints")),
            "pts_off_tov": _int(st.get("turnoverPoints")),
        })
    return rows


def parse_players(summary: dict) -> list[dict]:
    rows = []
    for tm in summary.get("boxscore", {}).get("players", []):
        team = tm["team"]["abbreviation"]
        for block in tm.get("statistics", []):
            keys = block.get("keys") or []
            for a in block.get("athletes", []):
                ath = a.get("athlete", {})
                stats = dict(zip(keys, a.get("stats") or []))
                minutes = _float(stats.get("minutes")) or 0.0
                dnp = int(bool(a.get("didNotPlay")) or minutes == 0)
                pid = ath.get("id")
                if pid is None:            # ESPN sometimes lists a name with no id
                    if dnp:
                        continue
                    pid = "name:" + (ath.get("displayName") or ath.get("shortName") or "?")
                fgm, fga = _made_att(stats.get("fieldGoalsMade-fieldGoalsAttempted"))
                f3m, f3a = _made_att(stats.get("threePointFieldGoalsMade-threePointFieldGoalsAttempted"))
                ftm, fta = _made_att(stats.get("freeThrowsMade-freeThrowsAttempted"))
                rows.append({
                    "team": team, "player_id": str(pid),
                    "name": ath.get("displayName") or ath.get("shortName") or "",
                    "position": (ath.get("position") or {}).get("abbreviation"),
                    "starter": int(bool(a.get("starter"))), "dnp": dnp,
                    "reason": a.get("reason") if dnp else None,
                    "minutes": minutes,
                    "pts": _int(stats.get("points")),
                    "fgm": fgm, "fga": fga, "fg3m": f3m, "fg3a": f3a, "ftm": ftm, "fta": fta,
                    "oreb": _int(stats.get("offensiveRebounds")),
                    "dreb": _int(stats.get("defensiveRebounds")),
                    "ast": _int(stats.get("assists")), "stl": _int(stats.get("steals")),
                    "blk": _int(stats.get("blocks")), "tov": _int(stats.get("turnovers")),
                    "pf": _int(stats.get("fouls")), "plus_minus": _int(stats.get("plusMinus")),
                })
    return rows


def _american(node: dict | None, key: str):
    """Odds node -> American odds int, e.g. node['moneyLine']['american'] = '+190'."""
    if not node:
        return None
    v = node.get(key)
    if isinstance(v, dict):
        v = v.get("american") or v.get("alternateDisplayValue")
    if v is None or v == "" or str(v).upper() == "OFF":
        return None
    if str(v).upper() in ("EVEN", "EV"):
        return 100
    return _int(v)


def _line(node: dict | None, key: str):
    if not node:
        return None
    v = node.get(key)
    if isinstance(v, dict):
        v = v.get("american") or v.get("alternateDisplayValue")
    if v is None or v == "" or str(v).upper() == "OFF":
        return None
    if str(v).lower() in ("pk", "pick", "ev", "even"):
        return 0.0
    return _float(v)


def parse_odds(data: dict) -> list[dict]:
    """One row per sportsbook ESPN lists (in-game "Live Odds" feeds are skipped)."""
    rows = []
    for item in data.get("items", []):
        name = item.get("provider", {}).get("name") or ""
        if not name or "live" in name.lower():
            continue
        h, a = item.get("homeTeamOdds") or {}, item.get("awayTeamOdds") or {}
        ho, hc = h.get("open"), h.get("close") or h.get("current")
        ao, ac = a.get("open"), a.get("close") or a.get("current")
        to, tc = item.get("open"), item.get("close") or item.get("current")

        spread_close = _line(hc, "pointSpread")
        if spread_close is None:
            spread_close = _float(item.get("spread"))
        total_close = _line(tc, "total")
        if total_close is None:
            total_close = _float(item.get("overUnder"))
        rows.append({
            "provider": name,
            "spread_open": _line(ho, "pointSpread"),
            "spread_close": spread_close,
            "home_spread_odds_open": _american(ho, "spread"),
            "away_spread_odds_open": _american(ao, "spread"),
            "home_spread_odds_close": _american(hc, "spread") or _int(h.get("spreadOdds")),
            "away_spread_odds_close": _american(ac, "spread") or _int(a.get("spreadOdds")),
            "total_open": _line(to, "total"),
            "total_close": total_close,
            "over_odds_open": _american(to, "over"),
            "under_odds_open": _american(to, "under"),
            "over_odds_close": _american(tc, "over") or _int(item.get("overOdds")),
            "under_odds_close": _american(tc, "under") or _int(item.get("underOdds")),
            "home_ml_open": _american(ho, "moneyLine"),
            "away_ml_open": _american(ao, "moneyLine"),
            "home_ml_close": _american(hc, "moneyLine") or _int(h.get("moneyLine")),
            "away_ml_close": _american(ac, "moneyLine") or _int(a.get("moneyLine")),
        })
    return rows


# ----------------------------------------------------------------------
# Storing
# ----------------------------------------------------------------------

GAME_COLS = ("game_id game_date start_utc season season_type home away home_score away_score "
             "home_reg away_reg periods state neutral").split()


def upsert_games(con, games: list[dict]) -> None:
    for g in games:
        con.execute(f"""
            INSERT INTO games ({", ".join(GAME_COLS)}, updated_at)
            VALUES ({", ".join(":" + c for c in GAME_COLS)}, :now)
            ON CONFLICT(game_id) DO UPDATE SET
                {", ".join(f"{c}=excluded.{c}" for c in GAME_COLS if c not in ("game_id", "neutral"))},
                neutral=MAX(games.neutral, excluded.neutral),
                updated_at=excluded.updated_at
        """, {**g, "now": now_iso()})


def fetch_detail(game_id: str, final: bool, home: str = "", away: str = "") -> dict:
    """Everything for one game. Network only - safe to run in threads."""
    out = {"game_id": game_id, "final": final}
    if final:
        s = get_json(SUMMARY, {"event": game_id})
        out["team_box"] = parse_team_box(s)
        out["players"] = parse_players(s)
        comp = (s.get("header", {}).get("competitions") or [{}])[0]
        out["neutral"] = int(bool(comp.get("neutralSite")))
        out["officials"] = "; ".join(o.get("displayName", "") for o in
                                     s.get("gameInfo", {}).get("officials", []))
        if len(out["team_box"]) < 2 and home and away:   # a few games have no box score there
            out["team_box"], out["players"] = fetch_box_core(game_id, home, away)
    out["odds"] = parse_odds(get_json(ODDS.format(g=game_id)))
    return out


CORE_EVENT = ("https://sports.core.api.espn.com/v2/sports/basketball/leagues/nba/events/{g}"
              "/competitions/{g}")


def _core_stats(ref: str | None) -> dict:
    """A core-API statistics page flattened to {stat name: value}."""
    if not ref:
        return {}
    cats = get_json(ref.replace("http://", "https://")).get("splits", {}).get("categories", [])
    return {s["name"]: s.get("value") for cat in cats for s in cat.get("stats", [])}


def fetch_box_core(game_id: str, home: str, away: str) -> tuple[list[dict], list[dict]]:
    """Backup box score from ESPN's core API (one request per player, so only used for the
    handful of games whose normal box score is missing)."""
    teams, players = [], []
    comp = get_json(CORE_EVENT.format(g=game_id))
    for c in comp.get("competitors", []):
        team = home if c.get("homeAway") == "home" else away
        st = _core_stats((c.get("statistics") or {}).get("$ref"))
        if not st:
            continue
        teams.append({
            "team": team,
            "fgm": _int(st.get("fieldGoalsMade")), "fga": _int(st.get("fieldGoalsAttempted")),
            "fg3m": _int(st.get("threePointFieldGoalsMade")),
            "fg3a": _int(st.get("threePointFieldGoalsAttempted")),
            "ftm": _int(st.get("freeThrowsMade")), "fta": _int(st.get("freeThrowsAttempted")),
            "oreb": _int(st.get("offensiveRebounds")), "dreb": _int(st.get("defensiveRebounds")),
            "ast": _int(st.get("assists")), "stl": _int(st.get("steals")),
            "blk": _int(st.get("blocks")),
            "tov": _int(st.get("totalTurnovers", st.get("turnovers"))),
            "pf": _int(st.get("fouls")), "pts_paint": _int(st.get("pointsInPaint")),
            "pts_fastbreak": _int(st.get("fastBreakPoints")),
            "pts_off_tov": _int(st.get("turnoverPoints")),
        })
        roster = get_json((c.get("roster") or {}).get("$ref", "").replace("http://", "https://")) \
            if c.get("roster") else {}
        for e in roster.get("entries", []):
            ps = _core_stats((e.get("statistics") or {}).get("$ref"))
            minutes = _float(ps.get("minutes")) or 0.0
            dnp = int(bool(e.get("didNotPlay")) or minutes == 0)
            pid = e.get("playerId")
            if pid is None:
                continue
            players.append({
                "team": team, "player_id": str(pid), "name": e.get("displayName") or "",
                "position": None, "starter": int(bool(e.get("starter"))), "dnp": dnp,
                "reason": e.get("reason") if dnp else None, "minutes": minutes,
                "pts": _int(ps.get("points")),
                "fgm": _int(ps.get("fieldGoalsMade")), "fga": _int(ps.get("fieldGoalsAttempted")),
                "fg3m": _int(ps.get("threePointFieldGoalsMade")),
                "fg3a": _int(ps.get("threePointFieldGoalsAttempted")),
                "ftm": _int(ps.get("freeThrowsMade")), "fta": _int(ps.get("freeThrowsAttempted")),
                "oreb": _int(ps.get("offensiveRebounds")), "dreb": _int(ps.get("defensiveRebounds")),
                "ast": _int(ps.get("assists")), "stl": _int(ps.get("steals")),
                "blk": _int(ps.get("blocks")), "tov": _int(ps.get("turnovers")),
                "pf": _int(ps.get("fouls")), "plus_minus": _int(ps.get("plusMinus")),
            })
    return teams, players


ODDS_COLS = ("spread_open spread_close home_spread_odds_open away_spread_odds_open "
             "home_spread_odds_close away_spread_odds_close total_open total_close "
             "over_odds_open under_odds_open over_odds_close under_odds_close "
             "home_ml_open away_ml_open home_ml_close away_ml_close").split()
TEAM_COLS = ("fgm fga fg3m fg3a ftm fta oreb dreb ast stl blk tov pf "
             "pts_paint pts_fastbreak pts_off_tov").split()
PLAYER_COLS = ("team player_id name position starter dnp reason minutes pts fgm fga fg3m fg3a "
               "ftm fta oreb dreb ast stl blk tov pf plus_minus").split()


def store_detail(con, d: dict) -> None:
    g = d["game_id"]
    if d["final"]:
        for r in d.get("team_box", []):
            con.execute(f"INSERT OR REPLACE INTO team_box (game_id, team, {', '.join(TEAM_COLS)}) "
                        f"VALUES (?, ?, {', '.join('?' * len(TEAM_COLS))})",
                        [g, r["team"]] + [r[c] for c in TEAM_COLS])
        for r in d.get("players", []):
            con.execute(f"INSERT OR REPLACE INTO players (game_id, {', '.join(PLAYER_COLS)}) "
                        f"VALUES (?, {', '.join('?' * len(PLAYER_COLS))})",
                        [g] + [r[c] for c in PLAYER_COLS])
        con.execute("UPDATE games SET neutral=MAX(neutral, ?), officials=? WHERE game_id=?",
                    (d.get("neutral", 0), d.get("officials"), g))
    stamp = now_iso()
    for o in d.get("odds") or []:
        con.execute(f"INSERT OR REPLACE INTO odds (game_id, provider, {', '.join(ODDS_COLS)}, "
                    f"is_final, fetched_at) VALUES (?, ?, {', '.join('?' * len(ODDS_COLS))}, ?, ?)",
                    [g, o["provider"]] + [o[c] for c in ODDS_COLS] + [int(d["final"]), stamp])
        if not d["final"]:
            _log_line(con, g, o, stamp)
    if d["final"] and len(d.get("team_box", [])) == 2:
        con.execute("UPDATE games SET detail_done=1 WHERE game_id=?", (g,))


def _log_line(con, game_id: str, o: dict, stamp: str) -> None:
    """Add a line_history row when the pre-game price differs from the last one we saw."""
    now = (o["spread_close"], o["home_spread_odds_close"], o["away_spread_odds_close"],
           o["total_close"], o["over_odds_close"], o["under_odds_close"],
           o["home_ml_close"], o["away_ml_close"])
    if all(v is None for v in now):
        return
    last = con.execute("""SELECT spread, home_spread_odds, away_spread_odds, total, over_odds,
                                 under_odds, home_ml, away_ml FROM line_history
                          WHERE game_id=? AND provider=? ORDER BY seen_at DESC LIMIT 1""",
                       (game_id, o["provider"])).fetchone()
    if last != now:
        con.execute("INSERT OR REPLACE INTO line_history VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    (game_id, o["provider"], stamp) + now)


# ----------------------------------------------------------------------
# Jobs
# ----------------------------------------------------------------------

def season_dates(first: int = FIRST_SEASON, until: date | None = None) -> list[date]:
    """Every date from 1 Oct to 30 Jun of each season, up to `until`."""
    until = until or datetime.now(ET).date() + timedelta(days=1)
    out = []
    for yr in range(first, until.year + 2):
        d, end = date(yr - 1, 10, 1), date(yr, 6, 30)
        while d <= end and d <= until:
            out.append(d)
            d += timedelta(days=1)
    return out


def sync_days(con, days: list[date], workers: int = 6) -> int:
    def one(d):
        return d, parse_scoreboard(get_json(SCOREBOARD, {"dates": d.strftime("%Y%m%d"), "limit": 100}))

    n = 0
    today = datetime.now(ET).date()
    with ThreadPoolExecutor(workers) as pool:
        for d, games in pool.map(one, days):
            upsert_games(con, games)
            n += len(games)
            if d < today - timedelta(days=2):
                con.execute("INSERT OR IGNORE INTO days_done VALUES (?)", (d.isoformat(),))
    con.commit()
    return n


def _safe_detail(game_id: str, final: bool, home: str = "", away: str = ""):
    try:
        return fetch_detail(game_id, final, home, away)
    except Exception as e:  # one bad game must not stop the backfill
        print(f"  ! {game_id}: {type(e).__name__}: {e}", file=sys.stderr)
        return None


def sync_details(con, workers: int = 6, quiet: bool = False) -> int:
    """Box scores + lines for finished games missing them, and fresh lines for
    games not started (today and the next 2 days)."""
    todo = [(g, True, h, a) for (g, h, a) in con.execute(
        "SELECT game_id, home, away FROM games WHERE state='post' AND detail_done=0 "
        "ORDER BY game_date")]
    soon = (datetime.now(ET).date() + timedelta(days=2)).isoformat()
    # Lines are only refreshed BEFORE tip-off: once a game is live ESPN shows in-game prices.
    todo += [(g, False, h, a) for (g, h, a) in con.execute(
        "SELECT game_id, home, away FROM games WHERE state='pre' AND game_date<=?", (soon,))]
    done, t0 = 0, time.time()
    with ThreadPoolExecutor(workers) as pool:
        for d in pool.map(lambda x: _safe_detail(*x), todo):
            if d:
                store_detail(con, d)
                done += 1
                if done % 500 == 0:
                    con.commit()
                    if not quiet:
                        print(f"  {done}/{len(todo)} games ({time.time() - t0:.0f}s)", flush=True)
    con.commit()
    return done


def backfill(con) -> None:
    done = {d for (d,) in con.execute("SELECT game_date FROM days_done")}
    days = [d for d in season_dates() if d.isoformat() not in done]
    print(f"Schedules: {len(days)} days to check...", flush=True)
    print(f"  {sync_days(con, days)} games found", flush=True)
    print("Box scores and sportsbook lines...", flush=True)
    print(f"  {sync_details(con)} games stored", flush=True)


def update(con, quiet: bool = False) -> None:
    """Last 5 days + next 2 days of schedules, then any missing details."""
    today = datetime.now(ET).date()
    days = [today + timedelta(days=i) for i in range(-5, 3)]
    days += [date.fromisoformat(d) for (d,) in con.execute(
        "SELECT DISTINCT game_date FROM games WHERE state IN ('pre','in') AND game_date<?",
        (today.isoformat(),))]
    sync_days(con, sorted(set(days)))
    sync_details(con, quiet=quiet)


def status(con) -> None:
    print("season  type  games  played  with box  with lines")
    for row in con.execute("""
        SELECT g.season, g.season_type, COUNT(*), SUM(g.state='post'), SUM(g.detail_done),
               SUM(EXISTS (SELECT 1 FROM odds o WHERE o.game_id=g.game_id
                           AND o.spread_close IS NOT NULL))
        FROM games g GROUP BY 1,2 ORDER BY 1,2"""):
        print("{:>6} {:>5} {:>6} {:>7} {:>9} {:>11}".format(*row))


# ----------------------------------------------------------------------
# One line per game, for the model and the backtest
# ----------------------------------------------------------------------

def _main_line(*prices) -> bool:
    """True when both sides are priced like a main line (about -110 each).

    Some stored "opening" lines are really alternate lines - a -20.5 spread at +320 on a game
    that closed -11.5. A lopsided price is the giveaway, so those are thrown out. A missing
    price is allowed (older rows have the number but not the price)."""
    return all(p is None or -131 <= p <= 111 for p in prices)


def load_lines(con) -> dict[str, dict]:
    """game_id -> one set of lines. Each market's numbers come from the first book in
    BOOK_ORDER that has a sane main line for it, so a spread and a total can come from
    different books when the preferred one has a gap."""
    rank = {name: i for i, name in enumerate(BOOK_ORDER)}
    cols = ["game_id", "provider"] + ODDS_COLS + ["is_final"]
    rows = [dict(zip(cols, r)) for r in con.execute(f"SELECT {', '.join(cols)} FROM odds")]
    rows.sort(key=lambda r: (r["game_id"], rank.get(r["provider"], 99), r["provider"]))
    out: dict[str, dict] = {}
    for r in rows:
        g = out.setdefault(r["game_id"], {"book_close": None, "book_open": None,
                                          **{c: None for c in ODDS_COLS}, "is_final": r["is_final"]})
        for when in ("close", "open"):
            sp = (r[f"home_spread_odds_{when}"], r[f"away_spread_odds_{when}"])
            if (g[f"spread_{when}"] is None and r[f"spread_{when}"] is not None
                    and abs(r[f"spread_{when}"]) <= 30 and _main_line(*sp)):
                g[f"spread_{when}"] = r[f"spread_{when}"]
                g[f"home_spread_odds_{when}"], g[f"away_spread_odds_{when}"] = sp
                g[f"home_ml_{when}"], g[f"away_ml_{when}"] = r[f"home_ml_{when}"], r[f"away_ml_{when}"]
                g[f"book_{when}"] = r["provider"]
            ou = (r[f"over_odds_{when}"], r[f"under_odds_{when}"])
            if (g[f"total_{when}"] is None and r[f"total_{when}"] is not None
                    and 150 <= r[f"total_{when}"] <= 300 and _main_line(*ou)):
                g[f"total_{when}"] = r[f"total_{when}"]
                g[f"over_odds_{when}"], g[f"under_odds_{when}"] = ou
    return out


def main(argv: list[str]) -> None:
    cmd = argv[1] if len(argv) > 1 else "update"
    con = connect()
    if cmd == "backfill":
        backfill(con)
        status(con)
    elif cmd == "update":
        update(con)
        status(con)
    elif cmd == "status":
        status(con)
    else:
        print(__doc__)


if __name__ == "__main__":
    main(sys.argv)
