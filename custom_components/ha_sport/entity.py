"""Base entity classes."""
from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, NAME, SPORTS, VERSION
from .coordinator import SportCoordinator
from .models import score_text


def compact_event(ev: dict[str, Any] | None) -> dict[str, Any] | None:
    """Small representation of an event for state attributes."""
    if not ev:
        return None
    odds = ev.get("odds") or {}
    streams = ev.get("streams") or []
    return {
        "id": ev["id"],
        "start": ev.get("start"),
        "sport": ev["sport"],
        "competition": ev.get("competition"),
        "round": ev.get("round"),
        "home": ev["home"]["name"],
        "away": ev["away"]["name"],
        "home_id": ev["home"]["id"],
        "away_id": ev["away"]["id"],
        "score": score_text(ev) if ev["status"] != "notstarted" else None,
        "status": ev["status"],
        "status_text": ev.get("status_text"),
        "minute": ev.get("minute"),
        "odds": {k: odds[k] for k in ("1", "X", "2") if k in odds} or None,
        "tv": [s["platform"] for s in streams] or None,
        "stream_url": streams[0]["url"] if streams else None,
        "city": ev.get("city"),
        "url": ev.get("url"),
    }


class SportEntity(CoordinatorEntity[SportCoordinator]):
    """Entity attached to the main integration device."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: SportCoordinator, key: str) -> None:
        super().__init__(coordinator)
        entry = coordinator.entry
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title or NAME,
            manufacturer="HA Sport",
            model="Sofascore data",
            sw_version=VERSION,
            entry_type=DeviceEntryType.SERVICE,
            configuration_url="https://www.sofascore.com/",
        )


class TeamEntity(CoordinatorEntity[SportCoordinator]):
    """Entity attached to a favorite team device."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: SportCoordinator, team: dict[str, Any], key: str) -> None:
        super().__init__(coordinator)
        self.team_id = int(team["id"])
        self.team = team
        entry = coordinator.entry
        self._attr_unique_id = f"{entry.entry_id}_team_{self.team_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry.entry_id}_team_{self.team_id}")},
            name=team.get("name") or f"Tým {self.team_id}",
            manufacturer="HA Sport",
            model=SPORTS.get(team.get("sport") or "", "Tým"),
            entry_type=DeviceEntryType.SERVICE,
            via_device=(DOMAIN, entry.entry_id),
            configuration_url=(
                f"https://www.sofascore.com/team/x/{self.team_id}" if self.team_id > 0
                else "https://www.hockeyslovakia.sk/sk/stats/tournaments"
            ),
        )
