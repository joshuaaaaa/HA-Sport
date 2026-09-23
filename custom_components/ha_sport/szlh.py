"""Second data source: HockeySlovakia.sk (Slovak Ice Hockey Federation, SZĽH).

Covers competitions Sofascore does not have – youth leagues (e.g. "Liga mladších
žiakov 6. ročník"), regional and lower leagues. The site has no public API, so
the server-rendered HTML is parsed. The parser does not rely on CSS classes: it
finds tables and recognises columns by their header texts, so small layout
changes of the site do not break it.
"""
from __future__ import annotations

import logging
import re
import zlib
from datetime import datetime, timedelta
from html.parser import HTMLParser
from typing import Any
from zoneinfo import ZoneInfo

from .const import STATUS_FINISHED, STATUS_NOT_STARTED
from .streams import normalize

_LOGGER = logging.getLogger(__name__)

BASE = "https://www.hockeyslovakia.sk"
TZ = ZoneInfo("Europe/Bratislava")
SOURCE = "szlh"
HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "sk-SK,sk;q=0.9,cs;q=0.8,en;q=0.7",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
}

TEAM_LINK_RE = re.compile(r"/team/(\d+)")
URL_RE = re.compile(r"/stats/[\w-]+/(\d+)(?:/([\w\-.%]+))?")
LINK_RE = re.compile(r"/(?:sk|en)/stats/[\w-]+/(\d+)(?:/([\w\-.%]+))?")
DATE_RE = re.compile(r"(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})")
# "So 27.09." / "27. 9." – date without a year (common on the site's match lists)
SHORT_DATE_RE = re.compile(r"(?:^|[\s(])(\d{1,2})\.\s*(\d{1,2})\.(?!\s*\d{4})(?!\d)")
TIME_RE = re.compile(r"^(\d{1,2})[:.](\d{2})$")
SCORE_RE = re.compile(r"(\d{1,2})\s*:\s*(\d{1,2})(?:\s*\(|\s*(pp|sn|PP|SN|p\.p\.|s\.n\.|pr\.|n\.)|\s*$)")
PAIR_RE = re.compile(r"^\s*(\d+)\s*:\s*(\d+)\s*$")


def find_date(text: str, today: datetime | None = None) -> tuple[int, int, int] | None:
    """(year, month, day) from '27. 9. 2026' or '27.09.' (year guessed around today)."""
    m = DATE_RE.search(text)
    if m:
        return int(m.group(3)), int(m.group(2)), int(m.group(1))
    m = SHORT_DATE_RE.search(text)
    if not m:
        return None
    day, month = int(m.group(1)), int(m.group(2))
    if not (1 <= day <= 31 and 1 <= month <= 12):
        return None
    today = today or datetime.now(TZ)
    # pick the year that puts the date closest to today (season crosses new year)
    best = None
    for year in (today.year - 1, today.year, today.year + 1):
        try:
            cand = datetime(year, month, day, tzinfo=TZ)
        except ValueError:
            continue
        diff = abs((cand - today).total_seconds())
        if best is None or diff < best[0]:
            best = (diff, year)
    return (best[1], month, day) if best else None


def _strip_dates(text: str) -> str:
    return SHORT_DATE_RE.sub(" ", DATE_RE.sub(" ", text))


def team_id(name: str) -> int:
    """Stable negative id for a team (never collides with Sofascore ids)."""
    return -(zlib.crc32(normalize(name).encode()) & 0x7FFFFFFF) or -1


def event_id(comp: str, date: str, home: str, away: str) -> int:
    key = f"{comp}|{date}|{normalize(home)}|{normalize(away)}"
    return -(zlib.crc32(key.encode()) & 0x7FFFFFFF) or -1


# --- minimal HTML table extractor ------------------------------------------------
class _Cell:
    __slots__ = ("text", "links", "header")

    def __init__(self, header: bool) -> None:
        self.text = ""
        self.links: list[str] = []
        self.header = header


class PageParser(HTMLParser):
    """Collect tables (rows of cells with text + links), headings and all links."""

    HEADINGS = {"h1", "h2", "h3", "h4", "h5", "caption", "legend"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tables: list[dict[str, Any]] = []
        self.links: list[tuple[str, str, str]] = []  # (href, text, heading)
        self._stack: list[dict[str, Any]] = []
        self._row: list[_Cell] | None = None
        self._cell: _Cell | None = None
        self._heading: str | None = None
        self._heading_buf: str | None = None
        self._link: list[Any] | None = None
        self._skip = 0
        self.title = ""
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = dict(attrs)
        if tag in ("script", "style"):
            self._skip += 1
        elif tag == "table":
            self._stack.append({"heading": self._heading, "rows": []})
        elif tag == "tr" and self._stack:
            self._row = []
        elif tag in ("td", "th") and self._row is not None:
            self._cell = _Cell(tag == "th")
        elif tag == "a":
            self._link = [a.get("href") or "", ""]
            if self._cell is not None and a.get("href"):
                self._cell.links.append(a["href"])
        elif tag in self.HEADINGS:
            self._heading_buf = ""
        elif tag == "title":
            self._in_title = True
        elif tag == "br" and self._cell is not None:
            self._cell.text += " "

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
        if tag in ("script", "style"):
            self._skip = max(0, self._skip - 1)
        elif tag in ("td", "th") and self._cell is not None and self._row is not None:
            self._cell.text = re.sub(r"\s+", " ", self._cell.text).strip()
            self._row.append(self._cell)
            self._cell = None
        elif tag == "tr" and self._row is not None and self._stack:
            if self._row:
                self._stack[-1]["rows"].append(self._row)
            self._row = None
        elif tag == "table" and self._stack:
            self.tables.append(self._stack.pop())
        elif tag == "a" and self._link is not None:
            href, text = self._link
            text = re.sub(r"\s+", " ", text).strip()
            if href:
                self.links.append((href, text, self._heading or ""))
            self._link = None
        elif tag in self.HEADINGS and self._heading_buf is not None:
            text = re.sub(r"\s+", " ", self._heading_buf).strip()
            if text:
                self._heading = text
            self._heading_buf = None

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title += data
        if self._skip:
            return
        if self._cell is not None:
            self._cell.text += data
        if self._link is not None:
            self._link[1] += data
        if self._heading_buf is not None:
            self._heading_buf += data


def parse_page(html: str) -> PageParser:
    parser = PageParser()
    parser.feed(html)
    parser.close()
    return parser


def parse_competition_url(value: str) -> tuple[int, str] | None:
    """'https://www.hockeyslovakia.sk/sk/stats/results/1207/liga-mladsich-ziakov-aa' -> (1207, slug)."""
    value = (value or "").strip()
    if value.isdigit():
        return int(value), ""
    m = URL_RE.search(value)
    if not m:
        return None
    return int(m.group(1)), m.group(2) or ""


def competition_name(html: str, slug: str = "") -> str | None:
    """Name from '<title>Súťaže a štatistiky | Liga mladších žiakov AA | Program a výsledky | …'."""
    parts = [p.strip() for p in parse_page(html).title.split("|") if p.strip()]
    if len(parts) >= 2 and "tatistiky" in parts[0]:
        return parts[1]
    if slug:
        return slug.replace("-", " ").capitalize()
    return parts[0] if parts else None


# --- tournaments -------------------------------------------------------------------
def parse_tournaments(html: str) -> list[dict[str, Any]]:
    """All competitions linked from /sk/stats/tournaments: [{id, slug, name, group}]."""
    found: dict[int, dict[str, Any]] = {}
    for href, text, heading in parse_page(html).links:
        m = LINK_RE.search(href)
        if not m or not text or len(text) < 3:
            continue
        tid = int(m.group(1))
        slug = m.group(2) or ""
        cur = found.get(tid)
        if cur is None or len(text) > len(cur["name"]):
            found[tid] = {"id": tid, "slug": slug or (cur or {}).get("slug", ""), "name": text, "group": heading}
        elif slug and not cur["slug"]:
            cur["slug"] = slug
    return sorted(found.values(), key=lambda t: normalize(t["name"]))


# --- standings ------------------------------------------------------------------------
COLUMN_KEYS = {
    "position": ("#", "por.", "poradie", "p.c.", "pc", "poz."),
    "team": ("tim", "timy", "druzstvo", "druzstva", "klub", "muzstvo", "team", "nazov"),
    "played": ("z", "zap", "zapasy", "zápasy", "gp", "odohrane"),
    "wins": ("v", "vyhry", "w"),
    "ot_wins": ("vp", "vpp", "vs", "vn", "vyhry pp", "otw"),
    "ot_losses": ("pp", "ppp", "ps", "pn", "prehry pp", "otl"),
    "draws": ("r", "remizy", "d", "n"),
    "losses": ("p", "prehry", "l"),
    "score": ("skore", "score", "goly", "g", "s"),
    "points": ("b", "body", "pts", "bodov"),
}


def _map_header(cells: list[str]) -> dict[str, int]:
    mapping: dict[str, int] = {}
    for idx, raw in enumerate(cells):
        key = normalize(raw).strip(" .:")
        for field, names in COLUMN_KEYS.items():
            if field in mapping:
                continue
            if key in {normalize(n).strip(" .:") for n in names}:
                mapping[field] = idx
                break
    return mapping


def _int(text: str | None) -> int | None:
    if text is None:
        return None
    m = re.search(r"-?\d+", text)
    return int(m.group()) if m else None


def parse_standings(html: str, logo: str | None = None) -> list[dict[str, Any]]:
    """Tables in the same shape as models.normalize_standings."""
    tables = []
    for table in parse_page(html).tables:
        rows = table["rows"]
        if len(rows) < 2:
            continue
        header_idx = next((i for i, r in enumerate(rows[:3]) if any(c.header for c in r) or _map_header([c.text for c in r]).get("team") is not None), None)
        mapping = _map_header([c.text for c in rows[header_idx]]) if header_idx is not None else {}
        body = rows[header_idx + 1:] if header_idx is not None else rows
        out_rows = []
        for r in body:
            texts = [c.text for c in r]
            if len(texts) < 3:
                continue
            if "team" in mapping and mapping["team"] < len(texts):
                team = texts[mapping["team"]]
            else:
                team = next((t for t in texts if re.search(r"[^\W\d_]{3,}", t)), None)
            if not team or not re.search(r"[^\W\d_]{2,}", team):
                continue
            team = re.sub(r"^\d+\.?\s+", "", team).strip()

            def col(field: str) -> str | None:
                idx = mapping.get(field)
                return texts[idx] if idx is not None and idx < len(texts) else None

            numbers = [t for t in texts if re.fullmatch(r"-?\d+\.?", t)]
            score = col("score") or next((t for t in texts if PAIR_RE.match(t)), None)
            pair = PAIR_RE.match(score or "")
            position = _int(col("position")) if "position" in mapping else (_int(numbers[0]) if numbers else None)
            points = _int(col("points")) if "points" in mapping else (_int(numbers[-1]) if numbers else None)
            played = _int(col("played")) if "played" in mapping else (_int(numbers[1]) if len(numbers) > 2 else None)
            out_rows.append(
                {
                    "position": position or len(out_rows) + 1,
                    "team_id": team_id(team),
                    "team": team,
                    "short": team,
                    "logo": logo,
                    "played": played,
                    "wins": _int(col("wins")),
                    "draws": _int(col("draws")),
                    "losses": _int(col("losses")),
                    "ot_wins": _int(col("ot_wins")),
                    "ot_losses": _int(col("ot_losses")),
                    "scores_for": int(pair.group(1)) if pair else None,
                    "scores_against": int(pair.group(2)) if pair else None,
                    "points": points,
                    "points_per_game": round(points / played, 2) if points is not None and played else None,
                    "percentage": None,
                    "promotion": None,
                    "promotion_id": None,
                }
            )
        # a standings table has a team column or scores ("33:7"); player stats tables have neither
        with_score = sum(1 for r in out_rows if r["scores_for"] is not None)
        if "team" not in mapping and with_score < max(2, len(out_rows) // 2):
            continue
        if len(out_rows) >= 2:
            tables.append({"name": table["heading"] or "Tabuľka", "rows": out_rows})
    return tables


# --- matches ---------------------------------------------------------------------------
def _is_team_text(text: str) -> bool:
    t = text.strip()
    if len(t) < 3 or not re.search(r"[^\W\d_]{3,}", t):
        return False
    if DATE_RE.search(t) or TIME_RE.match(t):
        return False
    if SHORT_DATE_RE.search(" " + t) and not re.search(r"[^\W\d_]{3,}", _strip_dates(" " + t)):
        return False  # "So 27.09." – a date cell, not a team
    low = normalize(t)
    return low not in {"detail", "zapis", "zapas", "online", "video", "live", "info", "stat", "report", "prenos"}


def parse_matches(html: str, comp: dict[str, Any], now: datetime | None = None) -> list[dict[str, Any]]:
    """Matches from a program / results page, normalized like models.normalize_event."""
    now = now or datetime.now(TZ)
    events: dict[int, dict[str, Any]] = {}
    for table in parse_page(html).tables:
        current_date: tuple[int, int, int] | None = None
        for row in table["rows"]:
            texts = [c.text for c in row]
            joined = " ".join(texts)
            found = find_date(" " + joined, now)
            if found:
                current_date = found
            linked = [c.text for c in row if any(TEAM_LINK_RE.search(h) for h in c.links) and _is_team_text(c.text)]
            team_cells = linked if len(linked) >= 2 else [t for t in texts if _is_team_text(t)]
            home = away = None
            if len(team_cells) >= 2:
                home, away = team_cells[0], team_cells[1]
            elif len(team_cells) == 1 and re.search(r"\s[-–]\s", team_cells[0]):
                home, away = re.split(r"\s[-–]\s", team_cells[0], maxsplit=1)
            if not home or not away or not current_date:
                continue
            hour = minute = None
            score = None
            for t in texts:
                t = t.strip()
                if DATE_RE.search(t) or SHORT_DATE_RE.search(" " + t):
                    # "12. 10. 2026 16:45" / "So 27.09. 16:45" – time in the same cell as the date
                    t = _strip_dates(" " + t).strip(" ,-")
                    t = re.sub(r"^[^\d]*", "", t)
                if _is_team_text(t):
                    continue
                tm = TIME_RE.match(t)
                if tm and int(tm.group(1)) <= 23 and hour is None and score is None:
                    hour, minute = int(tm.group(1)), int(tm.group(2))
                    continue
                sm = SCORE_RE.search(t)
                # once the kick-off time is known, "12:10" is a score, not a time
                if sm and score is None and (hour is not None or not TIME_RE.match(t)):
                    score = (int(sm.group(1)), int(sm.group(2)), (sm.group(3) or "").lower())
            y, mo, d = current_date
            try:
                start = datetime(y, mo, d, hour or 0, minute or 0, tzinfo=TZ)
            except ValueError:
                continue
            home = re.sub(r"\s+", " ", home).strip()
            away = re.sub(r"\s+", " ", away).strip()
            eid = event_id(str(comp["id"]), start.date().isoformat(), home, away)
            status = STATUS_FINISHED if score else STATUS_NOT_STARTED
            suffix = score[2] if score else ""
            status_text = "Konec" if score else "Nezačalo"
            if not score and start < now - timedelta(hours=3 if hour is not None else 24):
                status_text = "Výsledek zatím nezapsán"
            if suffix.startswith("pp") or suffix.startswith("p.p"):
                status_text = "Po prodloužení"
            elif suffix.startswith("sn") or suffix.startswith("s.n"):
                status_text = "Po nájezdech"
            winner = None
            if score:
                winner = 1 if score[0] > score[1] else 2 if score[1] > score[0] else 3
            events[eid] = {
                "id": eid,
                "source": SOURCE,
                "sport": "ice-hockey",
                "competition_id": comp["id"],
                "competition": comp.get("name"),
                "stage": table["heading"],
                "country": "SK",
                "category": "Slovakia",
                "season_id": None,
                "round": None,
                "round_number": None,
                "start": start.isoformat(),
                "timestamp": start.timestamp(),
                "status": status,
                "status_code": 100 if score else 0,
                "status_text": status_text,
                "minute": None,
                "home": {"id": team_id(home), "name": home, "short": home, "code": None, "logo": None,
                         "score": score[0] if score else None, "periods": [], "color": None},
                "away": {"id": team_id(away), "name": away, "short": away, "code": None, "logo": None,
                         "score": score[1] if score else None, "periods": [], "color": None},
                "winner": winner,
                "venue": None,
                "city": None,
                "url": comp.get("url"),
                "has_bracket": None,
                "odds": None,
                "tv": [],
                "streams": [],
                "time_known": hour is not None,
            }
    return sorted(events.values(), key=lambda e: e["timestamp"])


# --- client ------------------------------------------------------------------------------
class SzlhClient:
    """Fetches HockeySlovakia.sk pages (browser-like, curl_cffi when available)."""

    def __init__(self, session: Any) -> None:  # aiohttp.ClientSession
        self._session = session
        self.last_error: str | None = None

    async def _get(self, path: str) -> str | None:
        import aiohttp  # pylint: disable=import-outside-toplevel

        from .api import _get_curl_session  # pylint: disable=import-outside-toplevel

        url = path if path.startswith("http") else f"{BASE}{path}"
        errors = []
        curl = _get_curl_session()
        if curl is not None:
            try:
                resp = await curl.get(url, headers={k: v for k, v in HEADERS.items() if k != "User-Agent"})
                if resp.status_code == 200:
                    self.last_error = None
                    return resp.text
                errors.append(f"curl: HTTP {resp.status_code}")
            except Exception as exc:  # noqa: BLE001
                errors.append(f"curl: {exc}")
        try:
            async with self._session.get(url, headers=HEADERS, timeout=aiohttp.ClientTimeout(total=20)) as resp:
                if resp.status == 200:
                    self.last_error = None
                    return await resp.text()
                errors.append(f"aiohttp: HTTP {resp.status}")
        except (aiohttp.ClientError, TimeoutError) as exc:
            errors.append(f"aiohttp: {exc}")
        self.last_error = f"{url}: " + "; ".join(errors)
        _LOGGER.warning("HockeySlovakia.sk: %s", self.last_error)
        return None

    async def competition_from_url(self, value: str) -> dict[str, Any] | None:
        """Competition entry from a pasted HockeySlovakia.sk link (or numeric id)."""
        parsed = parse_competition_url(value)
        if not parsed:
            return None
        tid, slug = parsed
        html = await self._get(f"/sk/stats/results/{tid}/{slug}".rstrip("/"))
        name = competition_name(html, slug) if html else None
        if not name:
            name = slug.replace("-", " ").capitalize() if slug else f"SZĽH {tid}"
        return {"id": tid, "slug": slug, "name": name}

    async def tournaments(self) -> list[dict[str, Any]]:
        html = await self._get("/sk/stats/tournaments")
        return parse_tournaments(html) if html else []

    async def standings(self, comp: dict[str, Any]) -> list[dict[str, Any]]:
        html = await self._get(f"/sk/stats/standings/{comp['szlh_id']}/{comp.get('slug', '')}".rstrip("/"))
        return parse_standings(html) if html else []

    async def matches(self, comp: dict[str, Any]) -> list[dict[str, Any]]:
        """All matches of the competition (results page), falling back to the by-date view."""
        for kind in ("results", "results-date"):
            html = await self._get(f"/sk/stats/{kind}/{comp['szlh_id']}/{comp.get('slug', '')}".rstrip("/"))
            if not html:
                continue
            events = parse_matches(html, comp)
            if events:
                return events
        return []
