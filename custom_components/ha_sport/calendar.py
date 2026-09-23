"""Calendars with matches (all followed competitions / favorite teams)."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from . import SportConfigEntry
from .const import SPORT_EMOJI, SPORT_BASKETBALL, SPORT_HOCKEY, STATUS_NOT_STARTED
from .entity import SportEntity
from .models import score_text
from .notify_logic import odds_line

DURATION = {SPORT_HOCKEY: timedelta(hours=2, minutes=30), SPORT_BASKETBALL: timedelta(hours=2)}


async def async_setup_entry(
    hass: HomeAssistant, entry: SportConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coord = entry.runtime_data.coordinator
    async_add_entities([MatchCalendar(coord, favorites_only=False), MatchCalendar(coord, favorites_only=True)])


def _as_dt(value: date | datetime) -> datetime:
    if isinstance(value, datetime):
        return value
    return dt_util.start_of_local_day(value)


def to_calendar_event(ev: dict[str, Any]) -> CalendarEvent | None:
    start = dt_util.parse_datetime(ev["start"]) if ev.get("start") else None
    if not start:
        return None
    if ev.get("time_known") is False:
        # kick-off time unknown (SZĽH youth leagues) -> all-day event
        start = dt_util.as_local(start).date()
        end = start + timedelta(days=1)
    else:
        end = start + DURATION.get(ev["sport"], timedelta(hours=2))
    emoji = SPORT_EMOJI.get(ev["sport"], "")
    summary = f"{emoji} {ev['home']['name']} – {ev['away']['name']}"
    if ev["status"] != STATUS_NOT_STARTED:
        summary += f" ({score_text(ev)})"
    lines = [p for p in (ev.get("competition"), ev.get("round"), odds_line(ev)) if p]
    streams = ev.get("streams") or []
    if streams:
        lines.append("📺 " + ", ".join(f"{s['platform']}: {s['url']}" for s in streams))
    if ev.get("url"):
        lines.append(ev["url"])
    return CalendarEvent(
        start=start,
        end=end,
        summary=summary,
        description="\n".join(lines),
        location=", ".join(p for p in (ev.get("venue"), ev.get("city")) if p) or None,
        uid=f"ha_sport_{ev['id']}",
    )


class MatchCalendar(SportEntity, CalendarEntity):
    def __init__(self, coordinator, favorites_only: bool) -> None:
        super().__init__(coordinator, "calendar_favorites" if favorites_only else "calendar_all")
        self.favorites_only = favorites_only
        self._attr_translation_key = "favorites" if favorites_only else "all"
        self._attr_icon = "mdi:calendar-star" if favorites_only else "mdi:calendar-month"

    def _events(self) -> list[dict[str, Any]]:
        events = (self.coordinator.data or {}).get("events", [])
        if self.favorites_only:
            events = [e for e in events if e.get("favorite") or e.get("followed")]
        return events

    @property
    def event(self) -> CalendarEvent | None:
        now = dt_util.utcnow()
        for ev in self._events():
            cal = to_calendar_event(ev)
            if cal and _as_dt(cal.end) > now:
                return cal
        return None

    async def async_get_events(self, hass: HomeAssistant, start_date: datetime, end_date: datetime) -> list[CalendarEvent]:
        out = []
        for ev in self._events():
            cal = to_calendar_event(ev)
            if cal and _as_dt(cal.end) > start_date and _as_dt(cal.start) < end_date:
                out.append(cal)
        return out
