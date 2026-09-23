"""WebSocket API used by the Lovelace cards."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback

from .const import DOMAIN, SPORTS


def _runtimes(hass: HomeAssistant):
    from . import loaded_runtimes  # pylint: disable=import-outside-toplevel

    return loaded_runtimes(hass)


@callback
def async_register_websocket(hass: HomeAssistant) -> None:
    if hass.data[DOMAIN].get("ws_registered"):
        return
    for handler in (ws_overview, ws_matches, ws_competition, ws_team, ws_follow, ws_search, ws_favorite, ws_event_detail):
        websocket_api.async_register_command(hass, handler)
    hass.data[DOMAIN]["ws_registered"] = True


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/overview"})
@callback
def ws_overview(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    competitions: list[dict[str, Any]] = []
    favorites: list[dict[str, Any]] = []
    live = 0
    updated = None
    error = None
    for rt in _runtimes(hass):
        coord = rt.coordinator
        data = coord.data or {}
        for comp in data.get("competitions", {}).values():
            competitions.append(
                {k: comp.get(k) for k in ("id", "name", "sport", "country", "season", "has_bracket", "has_standings", "logo")}
            )
        for fav in coord.favorites.values():
            info = coord.teams.get(int(fav["id"]), {})
            favorites.append({**fav, "logo": f"{coord.logo_base}/team/{fav['id']}", "city": info.get("city")})
        live += len(data.get("live", []))
        updated = data.get("updated")
        error = data.get("error")
    connection.send_result(
        msg["id"],
        {
            "competitions": competitions,
            "favorites": favorites,
            "sports": SPORTS,
            "live_count": live,
            "updated": updated,
            "error": error,
            "notifications": [rt.notifier.enabled for rt in _runtimes(hass)][:1] or [False],
        },
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/matches",
        vol.Optional("sport"): vol.Any(None, vol.In(list(SPORTS))),
        vol.Optional("competition_id"): vol.Any(None, vol.Coerce(str)),
        vol.Optional("team_id"): vol.Any(None, vol.Coerce(int)),
        vol.Optional("query"): vol.Any(None, str),
        vol.Optional("city"): vol.Any(None, str),
        vol.Optional("status"): vol.Any(None, str),
        vol.Optional("favorites_only", default=False): bool,
        vol.Optional("days_ahead"): vol.Any(None, vol.Coerce(float)),
        vol.Optional("days_back"): vol.Any(None, vol.Coerce(float)),
        vol.Optional("limit", default=100): vol.Coerce(int),
    }
)
@callback
def ws_matches(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    from .services import query_matches  # pylint: disable=import-outside-toplevel

    params = {k: v for k, v in msg.items() if k not in ("id", "type") and v not in (None, "")}
    if not _runtimes(hass):
        connection.send_result(msg["id"], {"matches": []})
        return
    connection.send_result(msg["id"], {"matches": query_matches(hass, params)})


@websocket_api.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/competition", vol.Required("competition_id"): vol.Coerce(str)}
)
@callback
def ws_competition(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    for rt in _runtimes(hass):
        if msg["competition_id"] in rt.coordinator.competitions:
            payload = rt.coordinator.competition_payload(msg["competition_id"])
            payload["favorites"] = list(rt.coordinator.favorites)
            # attach match details to bracket blocks
            events = rt.coordinator.events
            for tree in payload.get("bracket", []):
                for rnd in tree["rounds"]:
                    for block in rnd["blocks"]:
                        block["matches"] = [
                            {
                                "id": e["id"],
                                "start": e.get("start"),
                                "status": e["status"],
                                "home_id": e["home"]["id"],
                                "home_score": e["home"].get("score"),
                                "away_score": e["away"].get("score"),
                                "odds": e.get("odds"),
                                "streams": e.get("streams"),
                            }
                            for e in (events.get(i) for i in block.get("events", []))
                            if e
                        ]
            connection.send_result(msg["id"], payload)
            return
    connection.send_error(msg["id"], "not_found", "Soutěž není sledována")


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/team", vol.Required("team_id"): vol.Coerce(int)})
@callback
def ws_team(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    runtimes = _runtimes(hass)
    if not runtimes:
        connection.send_error(msg["id"], "not_loaded", "HA Sport není načten")
        return
    connection.send_result(msg["id"], runtimes[0].coordinator.team_summary(msg["team_id"]))


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/follow",
        vol.Required("event_id"): vol.Coerce(int),
        vol.Required("follow"): bool,
    }
)
@websocket_api.async_response
async def ws_follow(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    await hass.services.async_call(
        DOMAIN,
        "follow_match" if msg["follow"] else "unfollow_match",
        {"event_id": msg["event_id"]},
        blocking=True,
    )
    connection.send_result(msg["id"], {"followed": msg["follow"]})


@websocket_api.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/search", vol.Required("query"): str, vol.Optional("sport"): vol.Any(None, str)}
)
@websocket_api.async_response
async def ws_search(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    from .services import search_teams  # pylint: disable=import-outside-toplevel

    runtimes = _runtimes(hass)
    teams = await search_teams(runtimes[0], msg["query"], msg.get("sport")) if runtimes else []
    connection.send_result(msg["id"], {"teams": teams})


@websocket_api.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/favorite", vol.Required("team_id"): vol.Coerce(int), vol.Required("favorite"): bool}
)
@websocket_api.require_admin
@websocket_api.async_response
async def ws_favorite(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    await hass.services.async_call(
        DOMAIN,
        "add_favorite" if msg["favorite"] else "remove_favorite",
        {"team_id": msg["team_id"]},
        blocking=True,
    )
    connection.send_result(msg["id"], {"favorite": msg["favorite"]})


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/event_detail", vol.Required("event_id"): vol.Coerce(int)})
@websocket_api.async_response
async def ws_event_detail(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    runtimes = _runtimes(hass)
    if not runtimes:
        connection.send_error(msg["id"], "not_loaded", "HA Sport není načten")
        return
    detail = await runtimes[0].coordinator.async_event_detail(msg["event_id"])
    connection.send_result(msg["id"], detail)
