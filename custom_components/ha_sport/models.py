"""Pure data helpers: normalization of raw API payloads, filtering, formatting.

This module has no Home Assistant dependency so it can be unit tested easily.
"""
from __future__ import annotations

from datetime import datetime, timezone
from fractions import Fraction
from typing import Any, Iterable

from .const import (
    IMAGE_BASE_URL,
    SPORT_FOOTBALL,
    SPORT_HOCKEY,
    STATUS_CANCELED,
    STATUS_FINISHED,
    STATUS_LIVE,
    STATUS_NOT_STARTED,
    STATUS_POSTPONED,
    WEB_BASE_URL,
)
from .streams import normalize

# Sofascore status codes
_HALFTIME_CODES = {31}  # football halftime
_PAUSE_CODES = {31, 32, 33, 34, 35, 80, 81, 82}  # breaks / pauses / overtime breaks
_PERIOD_START = {
    6: ("1. poločas", 0),
    7: ("2. poločas", 45),
    41: ("1. prodloužení", 90),
    42: ("2. prodloužení", 105),
    50: ("Penalty", None),
    13: ("1. třetina", 0),
    14: ("2. třetina", 20),
    15: ("3. třetina", 40),
    40: ("Prodloužení", 60),
    52: ("Nájezdy", None),
    1: ("1. čtvrtina", None),
    2: ("2. čtvrtina", None),
    3: ("3. čtvrtina", None),
    4: ("4. čtvrtina", None),
}

STATUS_CZ = {
    STATUS_NOT_STARTED: "Nezačalo",
    STATUS_LIVE: "Živě",
    STATUS_FINISHED: "Konec",
    STATUS_POSTPONED: "Odloženo",
    STATUS_CANCELED: "Zrušeno",
}

DESCRIPTION_CZ = {
    "1st half": "1. poločas",
    "2nd half": "2. poločas",
    "Halftime": "Poločas",
    "Ended": "Konec",
    "AET": "Po prodloužení",
    "AP": "Po penaltách",
    "After penalties": "Po penaltách",
    "After extra time": "Po prodloužení",
    "After overtime": "Po prodloužení",
    "After penalty shootout": "Po nájezdech",
    "1st period": "1. třetina",
    "2nd period": "2. třetina",
    "3rd period": "3. třetina",
    "Overtime": "Prodloužení",
    "Penalties": "Penalty",
    "Pause": "Přestávka",
    "Awaiting extra time": "Před prodloužením",
    "Extra time halftime": "Přestávka prodloužení",
    "1st extra": "1. prodloužení",
    "2nd extra": "2. prodloužení",
    "1st quarter": "1. čtvrtina",
    "2nd quarter": "2. čtvrtina",
    "3rd quarter": "3. čtvrtina",
    "4th quarter": "4. čtvrtina",
    "Not started": "Nezačalo",
    "Postponed": "Odloženo",
    "Canceled": "Zrušeno",
    "Interrupted": "Přerušeno",
    "Abandoned": "Předčasně ukončeno",
}


def team_logo(team_id: int | str | None, proxy_base: str | None = None) -> str | None:
    if not team_id:
        return None
    if proxy_base:
        return f"{proxy_base}/team/{team_id}"
    return f"{IMAGE_BASE_URL}/team/{team_id}/image"


def tournament_logo(ut_id: int | str | None, proxy_base: str | None = None) -> str | None:
    if not ut_id:
        return None
    if proxy_base:
        return f"{proxy_base}/tournament/{ut_id}"
    return f"{IMAGE_BASE_URL}/unique-tournament/{ut_id}/image"


def fraction_to_decimal(value: Any) -> float | None:
    """Convert a fractional odd ('13/10') or a decimal string to a decimal odd."""
    if value is None:
        return None
    try:
        text = str(value).strip()
        if "/" in text:
            return round(float(Fraction(text)) + 1.0, 2)
        return round(float(text), 2)
    except (ValueError, ZeroDivisionError):
        return None


def parse_odds(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    """Parse /event/{id}/odds/1/featured (or /all) into 1/X/2 decimal odds."""
    if not payload:
        return None
    market: dict[str, Any] | None = None
    featured = payload.get("featured")
    if isinstance(featured, dict):
        market = featured.get("default") or featured.get("fullTime") or next(
            (v for v in featured.values() if isinstance(v, dict)), None
        )
    if market is None:
        for m in payload.get("markets") or []:
            name = (m.get("marketName") or "").lower()
            if name in ("full time", "1x2", "home/away", "match winner", "winner"):
                market = m
                break
        if market is None and payload.get("markets"):
            market = payload["markets"][0]
    if not market:
        return None
    result: dict[str, Any] = {"market": market.get("marketName")}
    for choice in market.get("choices") or []:
        name = str(choice.get("name", "")).upper()
        dec = fraction_to_decimal(choice.get("fractionalValue") or choice.get("decimalValue"))
        initial = fraction_to_decimal(choice.get("initialFractionalValue"))
        if name in ("1", "X", "2") and dec:
            result[name] = dec
            if initial:
                result[f"{name}_initial"] = initial
            change = choice.get("change")
            if change:
                result[f"{name}_trend"] = "up" if change > 0 else "down"
    if not any(k in result for k in ("1", "X", "2")):
        return None
    # implied probabilities (normalized, margin removed)
    inv = {k: 1 / result[k] for k in ("1", "X", "2") if result.get(k)}
    total = sum(inv.values())
    if total:
        result["probability"] = {k: round(v / total * 100) for k, v in inv.items()}
    return result


def _score(score: dict[str, Any] | None) -> int | None:
    if not score:
        return None
    val = score.get("current", score.get("display"))
    try:
        return int(val) if val is not None else None
    except (TypeError, ValueError):
        return None


def _periods(score: dict[str, Any] | None) -> list[int]:
    out = []
    if not score:
        return out
    for i in range(1, 8):
        v = score.get(f"period{i}")
        if v is None:
            break
        out.append(v)
    return out


def live_minute(raw: dict[str, Any], sport: str, now_ts: float | None = None) -> str | None:
    """Compute a human readable in-play clock ("67'", "2. třetina 12'", ...)."""
    status = raw.get("status") or {}
    code = status.get("code")
    if status.get("type") != STATUS_LIVE:
        return None
    if code in _PAUSE_CODES:
        return translate_description(status.get("description")) or "Přestávka"
    time = raw.get("time") or {}
    start = time.get("currentPeriodStartTimestamp")
    if not start:
        return translate_description(status.get("description"))
    now_ts = now_ts or datetime.now(timezone.utc).timestamp()
    elapsed = max(0, int((now_ts - start) // 60))
    if sport == SPORT_FOOTBALL:
        label, base = _PERIOD_START.get(code, (None, None))
        if base is None:
            return label or translate_description(status.get("description"))
        minute = base + elapsed + 1
        limit = base + 45 if code in (6, 7) else base + 15
        if minute > limit:
            return f"{limit}+{minute - limit}'"
        return f"{minute}'"
    label = translate_description(status.get("description"))
    if sport == SPORT_HOCKEY:
        return f"{label} {min(elapsed + 1, 20)}'"
    return label


def translate_description(desc: str | None) -> str | None:
    if not desc:
        return None
    return DESCRIPTION_CZ.get(desc, desc)


def normalize_event(
    raw: dict[str, Any],
    sport: str | None = None,
    logo_base: str | None = None,
) -> dict[str, Any]:
    """Convert a Sofascore event object into a compact, stable dict."""
    tournament = raw.get("tournament") or {}
    unique = tournament.get("uniqueTournament") or {}
    category = tournament.get("category") or unique.get("category") or {}
    sport = sport or ((category.get("sport") or {}).get("slug")) or SPORT_FOOTBALL
    status = raw.get("status") or {}
    status_type = status.get("type") or STATUS_NOT_STARTED
    if status_type not in STATUS_CZ:
        status_type = STATUS_POSTPONED if "postpon" in status_type else status_type
    home = raw.get("homeTeam") or {}
    away = raw.get("awayTeam") or {}
    ts = raw.get("startTimestamp")
    start = datetime.fromtimestamp(ts, timezone.utc).isoformat() if ts else None
    round_info = raw.get("roundInfo") or {}
    round_name = round_info.get("name") or (
        f"{round_info['round']}. kolo" if round_info.get("round") else None
    )
    slug = raw.get("slug")
    custom = raw.get("customId")
    url = (
        f"{WEB_BASE_URL}/{slug}/{custom}#id:{raw.get('id')}"
        if slug and custom
        else f"{WEB_BASE_URL}/event/{raw.get('id')}"
    )
    home_score = raw.get("homeScore") or {}
    away_score = raw.get("awayScore") or {}
    venue = raw.get("venue") or {}

    def team(t: dict[str, Any], score: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": t.get("id"),
            "name": t.get("name"),
            "short": t.get("shortName") or t.get("name"),
            "code": t.get("nameCode"),
            "logo": team_logo(t.get("id"), logo_base),
            "score": _score(score),
            "periods": _periods(score),
            "color": (t.get("teamColors") or {}).get("primary"),
        }

    event = {
        "id": raw.get("id"),
        "sport": sport,
        "competition_id": unique.get("id") or tournament.get("id"),
        "competition": unique.get("name") or tournament.get("name"),
        "stage": tournament.get("name") if tournament.get("name") != unique.get("name") else None,
        "country": category.get("alpha2") or (category.get("country") or {}).get("alpha2"),
        "category": category.get("name"),
        "season_id": (raw.get("season") or {}).get("id"),
        "round": round_name,
        "round_number": round_info.get("round"),
        "start": start,
        "timestamp": ts,
        "status": status_type,
        "status_code": status.get("code"),
        "status_text": translate_description(status.get("description"))
        or STATUS_CZ.get(status_type, status_type),
        "minute": live_minute(raw, sport),
        "home": team(home, home_score),
        "away": team(away, away_score),
        "winner": raw.get("winnerCode"),
        "venue": (venue.get("stadium") or {}).get("name") or venue.get("name"),
        "city": (venue.get("city") or {}).get("name"),
        "url": url,
        "has_bracket": bool(raw.get("cupMatchesInRound")) or None,
        "odds": None,
        "tv": [],
        "streams": [],
    }
    return event


def normalize_team(raw: dict[str, Any], sport: str | None = None, logo_base: str | None = None) -> dict[str, Any]:
    team = raw.get("team", raw)
    venue = team.get("venue") or {}
    city = (venue.get("city") or {}).get("name")
    category = team.get("category") or {}
    return {
        "id": team.get("id"),
        "name": team.get("name"),
        "short": team.get("shortName") or team.get("name"),
        "code": team.get("nameCode"),
        "sport": sport or (team.get("sport") or {}).get("slug"),
        "country": (team.get("country") or {}).get("alpha2") or category.get("alpha2"),
        "city": city,
        "stadium": (venue.get("stadium") or {}).get("name"),
        "national": team.get("national", False),
        "logo": team_logo(team.get("id"), logo_base),
        "color": (team.get("teamColors") or {}).get("primary"),
    }


def normalize_standings(payload: dict[str, Any] | None, logo_base: str | None = None) -> list[dict[str, Any]]:
    """Return a list of tables (groups), each with rows."""
    tables = []
    for table in (payload or {}).get("standings") or []:
        rows = []
        for row in table.get("rows") or []:
            team = row.get("team") or {}
            promo = row.get("promotion") or {}
            rows.append(
                {
                    "position": row.get("position"),
                    "team_id": team.get("id"),
                    "team": team.get("name"),
                    "short": team.get("shortName") or team.get("name"),
                    "logo": team_logo(team.get("id"), logo_base),
                    "played": row.get("matches"),
                    "wins": row.get("wins"),
                    "draws": row.get("draws"),
                    "losses": row.get("losses"),
                    "ot_wins": row.get("overtimeWins"),
                    "ot_losses": row.get("overtimeLosses"),
                    "scores_for": row.get("scoresFor"),
                    "scores_against": row.get("scoresAgainst"),
                    "points": row.get("points"),
                    "percentage": row.get("percentage"),
                    "promotion": promo.get("text"),
                    "promotion_id": promo.get("id"),
                }
            )
        tables.append({"name": table.get("name"), "rows": rows})
    return tables


def normalize_bracket(payload: dict[str, Any] | None, logo_base: str | None = None) -> list[dict[str, Any]]:
    """Normalize /cuptrees into [{name, rounds:[{name, blocks:[...]}]}]."""
    trees = []
    for tree in (payload or {}).get("cupTrees") or []:
        rounds = []
        for rnd in sorted(tree.get("rounds") or [], key=lambda r: r.get("order", 0)):
            blocks = []
            for block in sorted(rnd.get("blocks") or [], key=lambda b: b.get("order", 0)):
                parts = []
                for p in sorted(block.get("participants") or [], key=lambda x: x.get("order", 0)):
                    team = p.get("team") or {}
                    parts.append(
                        {
                            "team_id": team.get("id"),
                            "name": team.get("name"),
                            "short": team.get("shortName") or team.get("name"),
                            "logo": team_logo(team.get("id"), logo_base),
                            "winner": p.get("winner", False),
                        }
                    )
                ts = block.get("seriesStartDateTimestamp")
                blocks.append(
                    {
                        "id": block.get("blockId") or block.get("id"),
                        "order": block.get("order"),
                        "finished": block.get("finished", False),
                        "live": block.get("eventInProgress", False),
                        "result": block.get("result"),
                        "home_score": block.get("homeTeamScore"),
                        "away_score": block.get("awayTeamScore"),
                        "participants": parts,
                        "events": block.get("events") or [],
                        "start": datetime.fromtimestamp(ts, timezone.utc).isoformat() if ts else None,
                    }
                )
            rounds.append(
                {
                    "order": rnd.get("order"),
                    "name": translate_round(rnd.get("description")),
                    "blocks": blocks,
                }
            )
        trees.append({"id": tree.get("id"), "name": tree.get("name"), "rounds": rounds})
    return trees


ROUND_CZ = {
    "final": "Finále",
    "semifinals": "Semifinále",
    "semifinal": "Semifinále",
    "quarterfinals": "Čtvrtfinále",
    "quarterfinal": "Čtvrtfinále",
    "round of 16": "Osmifinále",
    "1/8": "Osmifinále",
    "round of 32": "1/16 finále",
    "1/16": "1/16 finále",
    "round of 64": "1/32 finále",
    "match for 3rd place": "O 3. místo",
    "3rd place": "O 3. místo",
    "pre-playoff": "Předkolo play-off",
    "play-in": "Předkolo play-off",
    "qualification": "Kvalifikace",
}


def translate_round(name: str | None) -> str | None:
    if not name:
        return name
    return ROUND_CZ.get(name.strip().lower(), name)


def team_form(events: Iterable[dict[str, Any]], team_id: int, limit: int = 5) -> list[str]:
    """Return last results of a team as ['W','D','L',...] (newest first)."""
    finished = [
        e for e in events
        if e.get("status") == STATUS_FINISHED and team_id in (e["home"]["id"], e["away"]["id"])
    ]
    finished.sort(key=lambda e: e.get("timestamp") or 0, reverse=True)
    form = []
    for e in finished[:limit]:
        winner = e.get("winner")
        is_home = e["home"]["id"] == team_id
        if winner == 3 or winner is None and e["home"]["score"] == e["away"]["score"]:
            form.append("D")
        elif (winner == 1 and is_home) or (winner == 2 and not is_home):
            form.append("W")
        elif winner in (1, 2):
            form.append("L")
        else:
            hs, as_ = e["home"]["score"] or 0, e["away"]["score"] or 0
            mine, theirs = (hs, as_) if is_home else (as_, hs)
            form.append("W" if mine > theirs else "L" if mine < theirs else "D")
    return form


def matches_text(event: dict[str, Any], query: str | None, teams: dict[Any, dict[str, Any]] | None = None) -> bool:
    """Case/diacritics insensitive match on team names, competition and city."""
    if not query:
        return True
    teams = teams or {}
    terms = [t for t in normalize(query).replace(",", " ").split(" ") if t]
    haystack_parts = [
        event.get("competition"),
        event.get("city"),
        event.get("venue"),
        event["home"].get("name"),
        event["home"].get("short"),
        event["away"].get("name"),
        event["away"].get("short"),
    ]
    for side in ("home", "away"):
        info = teams.get(event[side].get("id")) or teams.get(str(event[side].get("id"))) or {}
        haystack_parts.extend([info.get("city"), info.get("stadium")])
    haystack = normalize(" ".join(p for p in haystack_parts if p))
    return all(term in haystack for term in terms)


def filter_events(
    events: Iterable[dict[str, Any]],
    *,
    sport: str | None = None,
    competition_id: int | None = None,
    team_id: int | None = None,
    query: str | None = None,
    city: str | None = None,
    status: str | None = None,
    favorites: Iterable[int] | None = None,
    start_ts: float | None = None,
    end_ts: float | None = None,
    teams: dict[Any, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    fav = set(int(f) for f in favorites) if favorites is not None else None
    out = []
    for e in events:
        if sport and e.get("sport") != sport:
            continue
        if competition_id and str(e.get("competition_id")) != str(competition_id):
            continue
        if team_id and int(team_id) not in (e["home"]["id"], e["away"]["id"]):
            continue
        if fav is not None and not ({e["home"]["id"], e["away"]["id"]} & fav):
            continue
        if status:
            wanted = {status} if isinstance(status, str) else set(status)
            if "upcoming" in wanted:
                wanted.add(STATUS_NOT_STARTED)
            if "results" in wanted:
                wanted.add(STATUS_FINISHED)
            if "live" in wanted:
                wanted.add(STATUS_LIVE)
            if e.get("status") not in wanted:
                continue
        ts = e.get("timestamp") or 0
        if start_ts is not None and ts < start_ts:
            continue
        if end_ts is not None and ts > end_ts:
            continue
        if not matches_text(e, query, teams):
            continue
        if city and not matches_text(
            {**e, "competition": None, "home": {**e["home"], "name": None, "short": None},
             "away": {**e["away"], "name": None, "short": None}},
            city,
            teams,
        ):
            continue
        out.append(e)
    return out


def event_title(event: dict[str, Any]) -> str:
    return f"{event['home']['name']} – {event['away']['name']}"


def score_text(event: dict[str, Any]) -> str:
    h, a = event["home"].get("score"), event["away"].get("score")
    if h is None or a is None:
        return "-:-"
    return f"{h}:{a}"


# --- Odds from several bookmakers -------------------------------------------------
def merge_bookmakers(sources: list[tuple[str, dict[str, Any]]]) -> dict[str, Any] | None:
    """Combine odds of several bookmakers.

    The first source stays the "main" odds (1/X/2 keys, trend), plus:
    ``bookmakers`` (all sources), ``best`` / ``best_bookmaker`` (highest odd per
    outcome) and ``probability`` averaged over all bookmakers (margin removed).
    """
    sources = [(name, o) for name, o in sources if o and o.get("1") and o.get("2")]
    if not sources:
        return None
    main = dict(sources[0][1])
    main["source"] = sources[0][0]
    main["bookmakers"] = [
        {"name": name, **{k: o.get(k) for k in ("1", "X", "2") if o.get(k)}} for name, o in sources
    ]
    best: dict[str, float] = {}
    best_bm: dict[str, str] = {}
    probs: dict[str, list[float]] = {}
    for name, o in sources:
        inv = {k: 1 / o[k] for k in ("1", "X", "2") if o.get(k)}
        total = sum(inv.values())
        for k, v in inv.items():
            if o[k] > best.get(k, 0):
                best[k], best_bm[k] = o[k], name
            probs.setdefault(k, []).append(v / total * 100)
    main["best"] = best
    main["best_bookmaker"] = best_bm
    main["probability"] = {k: round(sum(v) / len(v)) for k, v in probs.items()}
    return main


def odds_for_team(odds: dict[str, Any] | None, is_home: bool) -> dict[str, Any]:
    """Odds seen from one team's perspective."""
    odds = odds or {}
    mine, theirs = ("1", "2") if is_home else ("2", "1")
    return {
        "team": odds.get(mine),
        "draw": odds.get("X"),
        "opponent": odds.get(theirs),
        "team_initial": odds.get(f"{mine}_initial"),
        "team_trend": odds.get(f"{mine}_trend"),
        "team_best": (odds.get("best") or {}).get(mine),
        "team_best_bookmaker": (odds.get("best_bookmaker") or {}).get(mine),
        "probability": (odds.get("probability") or {}).get(mine),
        "probability_draw": (odds.get("probability") or {}).get("X"),
        "probability_opponent": (odds.get("probability") or {}).get(theirs),
    }


# --- Match detail -------------------------------------------------------------------
STAT_CZ = {
    "Ball possession": "Držení míče",
    "Expected goals": "Očekávané góly (xG)",
    "Total shots": "Střely",
    "Shots on target": "Střely na branku",
    "Shots off target": "Střely mimo",
    "Blocked shots": "Zblokované střely",
    "Corner kicks": "Rohy",
    "Offsides": "Ofsajdy",
    "Fouls": "Fauly",
    "Yellow cards": "Žluté karty",
    "Red cards": "Červené karty",
    "Goalkeeper saves": "Zákroky brankáře",
    "Passes": "Přihrávky",
    "Accurate passes": "Přesné přihrávky",
    "Big chances": "Velké šance",
    "Free kicks": "Přímé kopy",
    "Throw-ins": "Auty",
    "Tackles": "Skluzy",
    "Shots": "Střely",
    "Saves": "Zákroky",
    "Penalty minutes": "Trestné minuty",
    "Power play goals": "Góly v přesilovce",
    "Short-handed goals": "Góly v oslabení",
    "Faceoffs won": "Vhazování",
    "Hits": "Hity",
    "Free throws": "Trestné hody",
    "2 pointers": "Dvojky",
    "3 pointers": "Trojky",
    "Rebounds": "Doskoky",
    "Assists": "Asistence",
    "Turnovers": "Ztráty",
    "Steals": "Zisky",
    "Timeouts": "Oddechové časy",
}


def _player(p: dict[str, Any] | None) -> str | None:
    if not p:
        return None
    return p.get("shortName") or p.get("name")


def parse_incidents(raw: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """Goals, cards and period markers, oldest first."""
    out = []
    for inc in raw or []:
        kind = inc.get("incidentType")
        cls = inc.get("incidentClass")
        minute = inc.get("time")
        added = inc.get("addedTime")
        when = f"{minute}+{added}'" if minute is not None and added and added != 999 else (f"{minute}'" if minute is not None else "")
        if kind == "goal":
            out.append({
                "id": inc.get("id"), "type": "goal", "minute": when, "time": minute,
                "is_home": inc.get("isHome"), "player": _player(inc.get("player")),
                "assist": _player(inc.get("assist1")),
                "detail": {"penalty": "penalta", "ownGoal": "vlastní gól"}.get(cls),
                "score": f"{inc.get('homeScore')}:{inc.get('awayScore')}",
            })
        elif kind == "card":
            out.append({
                "id": inc.get("id"), "type": "card", "minute": when, "time": minute,
                "is_home": inc.get("isHome"), "player": _player(inc.get("player")) or inc.get("playerName"),
                "card": {"yellow": "yellow", "red": "red", "yellowRed": "second_yellow"}.get(cls, cls),
                "detail": inc.get("reason"),
            })
        elif kind == "period" and inc.get("text"):
            out.append({"type": "period", "text": inc.get("text"), "time": minute,
                        "score": f"{inc.get('homeScore')}:{inc.get('awayScore')}"})
        elif kind == "varDecision":
            out.append({"id": inc.get("id"), "type": "var", "minute": when, "time": minute,
                        "is_home": inc.get("isHome"), "detail": cls})
    out.sort(key=lambda i: (i.get("time") or 0))
    return out


def parse_statistics(payload: dict[str, Any] | None) -> list[dict[str, Any]]:
    for period in (payload or {}).get("statistics") or []:
        if period.get("period") != "ALL":
            continue
        items = []
        for group in period.get("groups") or []:
            for item in group.get("statisticsItems") or []:
                name = item.get("name")
                if any(i["key"] == name for i in items):
                    continue
                items.append({
                    "key": name,
                    "name": STAT_CZ.get(name, name),
                    "home": item.get("home"),
                    "away": item.get("away"),
                    "home_value": item.get("homeValue"),
                    "away_value": item.get("awayValue"),
                })
        return items
    return []


def parse_lineups(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    if not payload or not payload.get("home"):
        return None

    def side(data: dict[str, Any]) -> dict[str, Any]:
        players = data.get("players") or []
        return {
            "formation": data.get("formation"),
            "starters": [
                {"name": _player(p.get("player")), "number": p.get("shirtNumber") or p.get("jerseyNumber"), "position": p.get("position")}
                for p in players if not p.get("substitute")
            ],
            "substitutes": [_player(p.get("player")) for p in players if p.get("substitute")],
            "missing": [_player(m.get("player")) for m in data.get("missingPlayers") or []],
        }

    return {"confirmed": bool(payload.get("confirmed")), "home": side(payload["home"]), "away": side(payload.get("away") or {})}


def parse_h2h(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    duel = (payload or {}).get("teamDuel")
    if not duel:
        return None
    return {"home_wins": duel.get("homeWins", 0), "draws": duel.get("draws", 0), "away_wins": duel.get("awayWins", 0)}


def parse_votes(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    vote = (payload or {}).get("vote")
    if not vote:
        return None
    counts = {"1": vote.get("vote1") or 0, "X": vote.get("voteX") or 0, "2": vote.get("vote2") or 0}
    total = sum(counts.values())
    if not total:
        return None
    return {"total": total, **{k: round(v / total * 100) for k, v in counts.items()}}
