"""Поддельный TheSportsDB с теми же лимитами, что у бесплатного ключа."""
import json, re, datetime as dt
from urllib.parse import urlparse, parse_qs

SEASON = "2026-2027"
TODAY = dt.date.today()
TEAMS = ["Arsenal","Liverpool","Man City","Chelsea","Tottenham","Newcastle",
         "Aston Villa","Man United","Brighton","West Ham"]
CUR_ROUND = 3

def mk(idx, rnd, day_off, hour=17):
    d = TODAY + dt.timedelta(days=day_off)
    h = TEAMS[(idx*2) % 10]; a = TEAMS[(idx*2+1) % 10]
    past = day_off < 0
    return {"idEvent": f"{rnd}{idx:02d}", "strEvent": f"{h} vs {a}",
            "strHomeTeam": h, "strAwayTeam": a,
            "intHomeScore": str(idx % 4) if past else None,
            "intAwayScore": str((idx+1) % 3) if past else None,
            "intRound": str(rnd), "strSeason": SEASON,
            "strTimestamp": f"{d.isoformat()}T{hour:02d}:00:00",
            "dateEvent": d.isoformat(), "strTime": f"{hour:02d}:00:00",
            "strStatus": "FT" if past else "NS", "strVenue": f"{h} Stadium"}

def round_events(rnd, limit=5):
    # тур N: чем дальше от текущего, тем дальше по датам
    base = (rnd - CUR_ROUND) * 7 - 1
    return [mk(i, rnd, base + (0 if i < 3 else 1), 15 + (i % 3) * 2) for i in range(limit)]

def handle(url):
    u = urlparse(url); q = parse_qs(u.query); path = u.path.split("/")[-1]

    if path == "eventspastleague.php":
        return {"events": [mk(0, CUR_ROUND, -1)]}              # лимит: 1 матч
    if path == "eventsnextleague.php":
        return {"events": [mk(0, CUR_ROUND + 1, 6)]}
    if path == "eventsround.php":
        r = int(q.get("r", ["1"])[0]); s = q.get("s", [""])[0]
        if s != SEASON:                                        # сезон не тот — пусто
            return {"events": None}
        return {"events": round_events(r)}
    if path == "eventsday.php":
        d = q.get("d", [""])[0]
        out = []
        for rnd in range(CUR_ROUND - 1, CUR_ROUND + 2):
            out += [e for e in round_events(rnd) if e["dateEvent"] == d]
        return {"events": out[:3] or None}                     # лимит: 3 матча
    if path == "eventsseason.php":
        out = []
        for rnd in range(1, 4): out += round_events(rnd, 5)
        return {"events": out[:15]}
    if path == "lookuptable.php":
        return {"table": [{"intRank": str(i+1), "strTeam": TEAMS[i], "strBadge": "",
                           "intPlayed": "10", "intWin": str(8-i), "intDraw": "1",
                           "intLoss": str(1+i), "intGoalsFor": str(20-i),
                           "intGoalsAgainst": str(5+i), "intGoalDifference": str(15-2*i),
                           "intPoints": str(25-3*i), "strForm": "WWDLW",
                           "strDescription": "Promotion - Champions League (Group Stage)" if i < 4 else ""}
                          for i in range(5)]}                  # лимит: 5 строк
    return {}


# --- football-data.org: полная таблица ---
FD_TEAMS = ["Arsenal","Liverpool","Manchester City","Chelsea","Tottenham","Newcastle",
            "Aston Villa","Manchester United","Brighton","West Ham","Crystal Palace",
            "Fulham","Brentford","Everton","Nottingham Forest","Bournemouth",
            "Wolves","Leeds","Burnley","Sunderland"]

def handle_fd(url):
    n = len(FD_TEAMS)
    table = []
    for i, name in enumerate(FD_TEAMS):
        won = max(0, 9 - i // 2); draw = (i * 3) % 4; lost = 12 - won - draw
        table.append({
            "position": i + 1,
            "team": {"id": 100 + i, "name": name + " FC", "shortName": name,
                     "tla": name[:3].upper(), "crest": ""},
            "playedGames": 12, "form": ",".join(["W","D","L","W","W"][(i % 5):] + ["W","D","L","W","W"][:(i % 5)]),
            "won": won, "draw": draw, "lost": lost,
            "points": won * 3 + draw, "goalsFor": 30 - i, "goalsAgainst": 8 + i,
            "goalDifference": (30 - i) - (8 + i)})
    return {"competition": {"code": "PL", "name": "Premier League"},
            "season": {"currentMatchday": 12},
            "standings": [{"stage": "REGULAR_SEASON", "type": "TOTAL", "group": None, "table": table}]}


# --- OpenLigaDB: полная таблица без ключа ---
OL_TEAMS = ["FC Bayern München","Bayer 04 Leverkusen","RB Leipzig","VfB Stuttgart",
            "Borussia Dortmund","Eintracht Frankfurt","VfL Wolfsburg","SC Freiburg",
            "TSG Hoffenheim","SV Werder Bremen","1. FSV Mainz 05","FC Augsburg",
            "Borussia Mönchengladbach","1. FC Union Berlin","FC St. Pauli",
            "1. FC Heidenheim 1846","1. FC Köln","Hamburger SV"]

def handle_ol(url):
    out = []
    for i, name in enumerate(OL_TEAMS):
        won = max(0, 9 - i // 2); draw = (i * 3) % 4; lost = 12 - won - draw
        out.append({"teamInfoId": 100 + i, "teamName": name,
                    "shortName": name.split()[-1], "teamIconUrl": "",
                    "points": won * 3 + draw, "goals": 30 - i, "opponentGoals": 8 + i,
                    "matches": 12, "won": won, "lost": lost, "draw": draw,
                    "goalDiff": (30 - i) - (8 + i)})
    return out
