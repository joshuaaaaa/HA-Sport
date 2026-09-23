"""Match notifications: reminders before kick-off and live updates."""
from __future__ import annotations

import copy
import logging
import time
from datetime import datetime, timezone
from typing import Any, Callable

from homeassistant.components import persistent_notification
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers.event import async_track_point_in_utc_time
from homeassistant.util import dt as dt_util

from .const import (
    CONF_NOTIFY_BEFORE,
    CONF_NOTIFY_CARDS,
    CONF_NOTIFY_LINEUPS,
    CONF_NOTIFY_ODDS,
    CONF_ODDS_THRESHOLD,
    CONF_NOTIFY_ENABLED,
    CONF_NOTIFY_END,
    CONF_NOTIFY_LIVE_INTERVAL,
    CONF_NOTIFY_PERIODS,
    CONF_NOTIFY_PERSISTENT,
    CONF_NOTIFY_SCOPE,
    CONF_NOTIFY_SCORE,
    CONF_NOTIFY_START,
    CONF_NOTIFY_TARGETS,
    CONF_QUIET_END,
    CONF_QUIET_START,
    DEFAULT_NOTIFY_BEFORE,
    DEFAULT_NOTIFY_LIVE_INTERVAL,
    DEFAULT_ODDS_THRESHOLD,
    DOMAIN,
    EVENT_MATCH_UPDATE,
    EVENT_NOTIFICATION,
    EVENT_ODDS_CHANGE,
    NOTIFY_SCOPE_ALL,
    NOTIFY_SCOPE_FAVORITES,
    STATUS_LIVE,
    STATUS_NOT_STARTED,
)
from .coordinator import SportCoordinator
from .notify_logic import (
    Message,
    diff_messages,
    in_quiet_hours,
    live_update_message,
    odds_change_message,
    pre_match_message,
)

_LOGGER = logging.getLogger(__name__)

# a reminder that was missed (HA restart, API delay) is still sent within this window
CATCH_UP_SECONDS = 10 * 60


class SportNotifier:
    """Watches coordinator updates and dispatches notifications."""

    def __init__(self, hass: HomeAssistant, coordinator: SportCoordinator) -> None:
        self.hass = hass
        self.coordinator = coordinator
        self._prev: dict[int, dict[str, Any]] = {}
        self._timers: dict[str, tuple[float, CALLBACK_TYPE]] = {}
        self._unsub: Callable[[], None] | None = None
        self.enabled: bool = bool(coordinator.opt(CONF_NOTIFY_ENABLED, True))
        self.live_enabled: bool = True
        # odds value at the last alert (or first seen) per "event:outcome"
        self._odds_base: dict[str, float] = {}

    # --- lifecycle ------------------------------------------------------------
    @callback
    def async_start(self) -> None:
        self._unsub = self.coordinator.async_add_listener(self._handle_update)
        # initial snapshot, without sending diffs
        for ev in (self.coordinator.data or {}).get("events", []):
            self._check_odds(ev)
            self._prev[ev["id"]] = copy.deepcopy(ev)
        self._schedule_reminders()

    @callback
    def async_stop(self) -> None:
        if self._unsub:
            self._unsub()
            self._unsub = None
        for _, cancel in self._timers.values():
            cancel()
        self._timers.clear()

    # --- helpers ---------------------------------------------------------------
    def opt(self, key: str, default: Any = None) -> Any:
        return self.coordinator.opt(key, default)

    def in_scope(self, ev: dict[str, Any]) -> bool:
        eid = ev["id"]
        if eid in self.coordinator.muted:
            return False
        if eid in self.coordinator.followed:
            return True
        scope = self.opt(CONF_NOTIFY_SCOPE, NOTIFY_SCOPE_FAVORITES)
        if scope == NOTIFY_SCOPE_ALL:
            return True
        if scope == NOTIFY_SCOPE_FAVORITES:
            fav = self.coordinator.favorites
            return ev["home"]["id"] in fav or ev["away"]["id"] in fav
        return False  # NOTIFY_SCOPE_FOLLOWED -> only explicitly followed

    def _offsets(self) -> list[int]:
        out = []
        for v in self.opt(CONF_NOTIFY_BEFORE, DEFAULT_NOTIFY_BEFORE) or []:
            try:
                out.append(int(v))
            except (TypeError, ValueError):
                continue
        return sorted(set(out), reverse=True)

    # --- update handling --------------------------------------------------------
    @callback
    def _handle_update(self) -> None:
        data = self.coordinator.data or {}
        now = time.time()
        for ev in data.get("events", []):
            old = self._prev.get(ev["id"])
            if old and (
                old["status"] != ev["status"]
                or old["home"].get("score") != ev["home"].get("score")
                or old["away"].get("score") != ev["away"].get("score")
            ):
                self.hass.bus.async_fire(
                    EVENT_MATCH_UPDATE,
                    {
                        "event_id": ev["id"],
                        "sport": ev["sport"],
                        "competition": ev.get("competition"),
                        "home": ev["home"]["name"],
                        "away": ev["away"]["name"],
                        "home_score": ev["home"].get("score"),
                        "away_score": ev["away"].get("score"),
                        "status": ev["status"],
                        "old_status": old["status"],
                        "minute": ev.get("minute"),
                        "favorite": ev.get("favorite", False),
                    },
                )
            if self.in_scope(ev) and self.live_enabled:
                for msg in diff_messages(
                    old,
                    ev,
                    notify_start=self.opt(CONF_NOTIFY_START, True),
                    notify_score=self.opt(CONF_NOTIFY_SCORE, True),
                    notify_periods=self.opt(CONF_NOTIFY_PERIODS, False),
                    notify_end=self.opt(CONF_NOTIFY_END, True),
                    notify_cards=self.opt(CONF_NOTIFY_CARDS, True),
                    notify_lineups=self.opt(CONF_NOTIFY_LINEUPS, True),
                ):
                    self._send(msg)
                interval = int(self.opt(CONF_NOTIFY_LIVE_INTERVAL, DEFAULT_NOTIFY_LIVE_INTERVAL) or 0)
                if interval > 0 and ev["status"] == STATUS_LIVE and ev.get("timestamp"):
                    slot = int((now - ev["timestamp"]) // (interval * 60))
                    if slot > 0:
                        self._send(live_update_message(ev, slot))
            self._check_odds(ev)
            self._prev[ev["id"]] = copy.deepcopy(ev)
        self._schedule_reminders()

    @callback
    def _check_odds(self, ev: dict[str, Any]) -> None:
        """Alert when the odd on my team moved by the threshold since the last alert."""
        odds = ev.get("odds") or {}
        if ev["status"] != STATUS_NOT_STARTED or not odds:
            return
        fav = self.coordinator.favorites
        outcomes = [o for o, side in (("1", "home"), ("2", "away")) if ev[side]["id"] in fav]
        if not outcomes and ev["id"] in self.coordinator.followed:
            outcomes = ["1", "2"]
        threshold = float(self.opt(CONF_ODDS_THRESHOLD, DEFAULT_ODDS_THRESHOLD) or DEFAULT_ODDS_THRESHOLD)
        for outcome in outcomes:
            if not odds.get(outcome):
                continue
            key = f"{ev['id']}:{outcome}"
            base = self._odds_base.setdefault(key, odds[outcome])
            msg = odds_change_message({"odds": {outcome: base}}, ev, outcome, threshold)
            if msg is None:
                continue
            self._odds_base[key] = odds[outcome]
            self.hass.bus.async_fire(
                EVENT_ODDS_CHANGE,
                {"event_id": ev["id"], "home": ev["home"]["name"], "away": ev["away"]["name"], **msg.extra},
            )
            if self.opt(CONF_NOTIFY_ODDS, False) and self.in_scope(ev):
                self._send(msg)

    @callback
    def _schedule_reminders(self) -> None:
        data = self.coordinator.data or {}
        now = time.time()
        offsets = self._offsets()
        wanted: dict[str, float] = {}
        for ev in data.get("events", []):
            if ev["status"] != STATUS_NOT_STARTED or not ev.get("timestamp"):
                continue
            if not self.in_scope(ev):
                continue
            for minutes in offsets:
                if ev.get("time_known") is False and minutes < 1440:
                    continue  # kick-off time unknown (SZĽH): only day-before reminders make sense
                fire_at = ev["timestamp"] - minutes * 60
                key = f"{ev['id']}:pre:{minutes}"
                if key in self.coordinator.sent_keys or ev["timestamp"] <= now:
                    continue
                if fire_at <= now:
                    if now - fire_at <= CATCH_UP_SECONDS:
                        self._send(pre_match_message(ev, minutes, dt_util.get_default_time_zone()))
                    continue
                wanted[key] = fire_at
        # cancel timers no longer needed / rescheduled
        for key in list(self._timers):
            if key not in wanted or self._timers[key][0] != wanted[key]:
                self._timers.pop(key)[1]()
        for key, fire_at in wanted.items():
            if key in self._timers:
                continue
            eid, _, minutes = key.split(":")
            self._timers[key] = (
                fire_at,
                async_track_point_in_utc_time(
                    self.hass,
                    self._make_reminder(int(eid), int(minutes), key),
                    datetime.fromtimestamp(fire_at, timezone.utc),
                ),
            )

    def _make_reminder(self, event_id: int, minutes: int, key: str):
        @callback
        def _fire(_now: datetime) -> None:
            self._timers.pop(key, None)
            ev = self.coordinator.events.get(event_id)
            if ev and ev["status"] == STATUS_NOT_STARTED and self.in_scope(ev):
                self._send(pre_match_message(ev, minutes, dt_util.get_default_time_zone()))

        return _fire

    # --- dispatch ---------------------------------------------------------------
    @callback
    def _send(self, msg: Message, force: bool = False) -> None:
        if msg.key in self.coordinator.sent_keys and not force:
            return
        self.coordinator.sent_keys[msg.key] = time.time()
        self.coordinator.async_schedule_save()
        ev = msg.event
        stream = (ev.get("streams") or [{}])[0].get("url")
        payload = {
            "kind": msg.kind,
            "title": msg.title,
            "message": msg.message,
            "event_id": ev["id"],
            "sport": ev["sport"],
            "competition": ev.get("competition"),
            "home": ev["home"]["name"],
            "away": ev["away"]["name"],
            "home_score": ev["home"].get("score"),
            "away_score": ev["away"].get("score"),
            "start": ev.get("start"),
            "odds": ev.get("odds"),
            "streams": ev.get("streams"),
            "url": ev.get("url"),
            **msg.extra,
        }
        # the bus event is always fired so users can build their own automations
        self.hass.bus.async_fire(EVENT_NOTIFICATION, payload)
        if not self.enabled and not force:
            return
        if in_quiet_hours(dt_util.now(), self.opt(CONF_QUIET_START), self.opt(CONF_QUIET_END)) and not force:
            _LOGGER.debug("Quiet hours – suppressed %s", msg.title)
            return
        if self.opt(CONF_NOTIFY_PERSISTENT, False):
            persistent_notification.async_create(
                self.hass,
                msg.message + (f"\n\n[Sledovat]({stream}) · [Detail]({ev.get('url')})" if stream else ""),
                title=msg.title,
                notification_id=f"{DOMAIN}_{ev['id']}",
            )
        for target in self.opt(CONF_NOTIFY_TARGETS, []) or []:
            service = target.split(".", 1)[1] if target.startswith("notify.") else target
            data: dict[str, Any] = {"title": msg.title, "message": msg.message}
            if service.startswith("mobile_app"):
                actions = []
                if stream:
                    actions.append({"action": "URI", "title": "📺 Sledovat", "uri": stream})
                if ev.get("url"):
                    actions.append({"action": "URI", "title": "Detail zápasu", "uri": ev["url"]})
                data["data"] = {
                    "tag": f"{DOMAIN}_{ev['id']}",
                    "group": DOMAIN,
                    "url": stream or ev.get("url"),
                    "clickAction": stream or ev.get("url"),
                    "actions": actions,
                    "channel": "Sport",
                    "importance": "high" if msg.kind in ("score", "start", "pre_match") else "default",
                }
            self.hass.async_create_task(
                self._call_notify(service, data), f"{DOMAIN}_notify_{service}"
            )

    async def _call_notify(self, service: str, data: dict[str, Any]) -> None:
        try:
            await self.hass.services.async_call("notify", service, data, blocking=True)
        except Exception as exc:  # noqa: BLE001 - never break the update loop
            _LOGGER.warning("Odeslání notifikace přes notify.%s selhalo: %s", service, exc)

    @callback
    def async_test(self) -> None:
        """Send a test notification with the nearest match."""
        events = (self.coordinator.data or {}).get("events", [])
        upcoming = [e for e in events if e["status"] == STATUS_NOT_STARTED]
        ev = next((e for e in upcoming if e.get("favorite")), upcoming[0] if upcoming else None)
        if ev is None:
            persistent_notification.async_create(
                self.hass, "Žádný nadcházející zápas k otestování.", title="HA Sport"
            )
            return
        msg = pre_match_message(ev, 15, dt_util.get_default_time_zone())
        msg.key = f"test:{time.time()}"
        self._send(msg, force=True)
