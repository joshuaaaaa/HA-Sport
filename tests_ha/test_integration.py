from unittest.mock import patch

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_capture_events

from custom_components.ha_sport.const import DOMAIN, EVENT_NOTIFICATION

from .conftest import NOW, UT, event

ENTRY_DATA = {
    "sports": ["football"],
    "countries": ["CZ"],
    "competitions": [{"id": UT, "sport": "football", "country": "CZ", "name": "Chance Liga"}],
    "favorite_teams": [{"id": 1, "name": "Team 1", "sport": "football"}],
    "notify_enabled": True,
    "notify_scope": "favorites",
    "notify_before": ["60", "15"],
    "notify_start": True,
    "notify_score": True,
    "notify_periods": False,
    "notify_end": True,
    "notify_live_interval": 0,
    "notify_targets": [],
    "notify_persistent": True,
}


async def test_config_flow(hass: HomeAssistant, fake_api) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] is FlowResultType.FORM and result["step_id"] == "user"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"sports": ["football"], "countries": ["CZ", "SK"], "base_url": "https://www.sofascore.com/api/v1"}
    )
    assert result["step_id"] == "competitions"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"competitions": [f"football|CZ|{UT}|Chance Liga"]}
    )
    assert result["step_id"] == "favorites"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"favorite_teams": ["football|1|Team 1"], "search": "Kometa"}
    )
    assert result["step_id"] == "search"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"results": ["ice-hockey|77|HC Kometa Brno"]})
    assert result["step_id"] == "favorites"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"favorite_teams": ["football|1|Team 1", "ice-hockey|77|HC Kometa Brno"]}
    )
    assert result["step_id"] == "notifications"
    with patch("custom_components.ha_sport.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"notify_enabled": True, "notify_scope": "favorites", "notify_before": ["15", "45"], "notify_start": True,
             "notify_score": True, "notify_periods": False, "notify_end": True, "notify_live_interval": 15,
             "notify_targets": [], "notify_persistent": False},
        )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert [t["id"] for t in result["data"]["favorite_teams"]] == [1, 77]
    assert result["data"]["competitions"][0]["id"] == UT
    assert result["data"]["notify_before"] == ["15", "45"]


async def _setup(hass: HomeAssistant) -> MockConfigEntry:
    entry = MockConfigEntry(domain=DOMAIN, data=ENTRY_DATA, title="HA Sport")
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_setup_entities_ws_services(hass: HomeAssistant, hass_ws_client, fake_api) -> None:
    entry = await _setup(hass)
    coord = entry.runtime_data.coordinator
    assert 101 in coord.events and coord.events[101]["odds"]["1"] == 2.0
    assert coord.events[101]["streams"][0]["platform"] == "Oneplay"

    states = {s.entity_id: s for s in hass.states.async_all()}
    next_sensor = next(s for eid, s in states.items() if eid.startswith("sensor.team_1") and s.attributes.get("event_id") == 101)
    assert next_sensor.attributes["odds_team"] == 2.0
    assert next_sensor.attributes["home_away"] == "doma"
    assert next_sensor.attributes["stream_url"] == "https://www.oneplay.cz/"
    assert next_sensor.attributes["form"] == "W"
    assert any(eid.startswith("calendar.") for eid in states)
    assert any(eid.startswith("switch.") for eid in states)
    pos = next(s for eid, s in states.items() if eid.startswith("sensor.team_1") and s.attributes.get("points") == 23)
    assert pos.state == "1"

    client = await hass_ws_client(hass)
    await client.send_json({"id": 1, "type": "ha_sport/overview"})
    msg = await client.receive_json()
    assert msg["success"] and msg["result"]["competitions"][0]["has_bracket"] is True

    await client.send_json({"id": 2, "type": "ha_sport/matches", "status": "upcoming", "query": "team 3"})
    msg = await client.receive_json()
    assert [m["id"] for m in msg["result"]["matches"]] == [102]

    await client.send_json({"id": 3, "type": "ha_sport/competition", "competition_id": str(UT)})
    msg = await client.receive_json()
    block = msg["result"]["bracket"][0]["rounds"][0]["blocks"][0]
    assert block["matches"][0]["id"] == 101 and msg["result"]["standings"][0]["rows"][0]["points"] == 23

    await client.send_json({"id": 4, "type": "ha_sport/team", "team_id": 1})
    msg = await client.receive_json()
    assert msg["result"]["next"]["id"] == 101 and msg["result"]["position"]["position"] == 1

    await client.send_json({"id": 5, "type": "ha_sport/follow", "event_id": 102, "follow": True})
    msg = await client.receive_json()
    assert msg["success"] and 102 in coord.followed

    resp = await hass.services.async_call(DOMAIN, "get_matches", {"city": "praha"}, blocking=True, return_response=True)
    assert 101 in [m["id"] for m in resp["matches"]]
    resp = await hass.services.async_call(DOMAIN, "search_team", {"query": "Kometa"}, blocking=True, return_response=True)
    assert resp["teams"][0]["id"] == 77


async def test_live_notifications(hass: HomeAssistant, fake_api) -> None:
    entry = await _setup(hass)
    coord = entry.runtime_data.coordinator
    events = async_capture_events(hass, EVENT_NOTIFICATION)

    # match 101 goes live with a goal for favorite team 1
    fake_api.live = [event(101, 1, 2, NOW - 600, "inprogress", 0, 0, 6)]
    coord.events[101]["timestamp"] = NOW - 600
    await coord.async_refresh()
    await hass.async_block_till_done()
    assert coord.events[101]["status"] == "inprogress"
    fake_api.live = [event(101, 1, 2, NOW - 600, "inprogress", 1, 0, 6)]
    await coord.async_refresh()
    await hass.async_block_till_done()
    kinds = [e.data["kind"] for e in events]
    assert "start" in kinds and "score" in kinds
    assert coord.update_interval.total_seconds() <= 60
    playing = [s for s in hass.states.async_all("binary_sensor") if s.attributes.get("event_id") == 101 and s.state == "on"]
    assert playing

    # match ends: removed from live feed, detail says finished
    fake_api.live = []
    fake_api.responses["/event/101"] = {"event": event(101, 1, 2, NOW - 6000, "finished", 2, 0, 100, 1)}
    await coord.async_refresh()
    await hass.async_block_till_done()
    assert "end" in [e.data["kind"] for e in events]
    # no duplicates
    assert len([e for e in events if e.data["kind"] == "end"]) == 1


async def test_reminder_catch_up_and_unload(hass: HomeAssistant, fake_api) -> None:
    ev = event(101, 1, 2, NOW + 10 * 60)
    fake_api.responses["/team/1/events/next/0"] = {"events": [ev]}
    events = async_capture_events(hass, EVENT_NOTIFICATION)
    entry = await _setup(hass)
    await hass.async_block_till_done()
    pre = [e.data for e in events if e.data["kind"] == "pre_match"]
    assert pre and pre[0]["minutes"] == 15
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_logo_proxy_registered(hass: HomeAssistant, hass_client, fake_api) -> None:
    await async_setup_component(hass, "http", {})
    await _setup(hass)
    client = await hass_client()
    # invalid kind -> 404 from our view (proves the route exists), card is no longer served
    assert (await client.get("/api/ha_sport/logo/foo/1")).status == 404
    assert (await client.get("/ha_sport_static/ha-sport-card.js")).status == 404


async def test_odds_multiple_bookmakers_and_sensors(hass: HomeAssistant, hass_ws_client, fake_api) -> None:
    entry = await _setup(hass)
    coord = entry.runtime_data.coordinator
    assert [p["name"] for p in coord.providers] == ["Tipsport", "Fortuna"]
    # favorite match: default + Tipsport compared, best odd picked
    odds = coord.events[101]["odds"]
    assert [b["name"] for b in odds["bookmakers"]] == ["Sofascore", "Tipsport"]
    assert odds["best"]["1"] == 2.1 and odds["best_bookmaker"]["1"] == "Tipsport"
    # non favorite match without default odds falls back to the local bookmaker
    assert coord.events[102]["odds"]["1"] == 1.5 and coord.events[102]["odds"]["source"] == "Tipsport"
    # pre-match detail for favorites
    assert coord.events[101]["h2h"]["home_wins"] == 4
    assert coord.events[101]["votes"]["1"] == 60
    assert "lineups" not in coord.events[101]  # lineups are polled only 90 min before kick-off

    win_odds = next(s for s in hass.states.async_all("sensor") if s.attributes.get("best_bookmaker") == "Tipsport")
    assert float(win_odds.state) == 2.0 and win_odds.attributes["best_odds"] == 2.1
    prob = next(s for s in hass.states.async_all("sensor") if s.attributes.get("unit_of_measurement") == "%"
                and s.attributes.get("event_id") == 101)
    assert 40 <= int(prob.state) <= 60

    client = await hass_ws_client(hass)
    await client.send_json({"id": 1, "type": "ha_sport/event_detail", "event_id": 101})
    msg = await client.receive_json()
    assert msg["success"]
    detail = msg["result"]
    assert detail["lineups"]["home"]["formation"] == "3-4-3"
    assert detail["h2h"]["draws"] == 3


async def test_goal_scorer_red_card_and_odds_alert(hass: HomeAssistant, fake_api) -> None:
    from homeassistant.core import callback  # noqa: F401

    entry = await _setup(hass)
    coord = entry.runtime_data.coordinator
    events = async_capture_events(hass, EVENT_NOTIFICATION)
    odds_events = async_capture_events(hass, "ha_sport_odds_change")

    # odds on my team (home, Team 1) drop from 2.0 to 1.5 -> ha_sport_odds_change
    fake_api.responses["/event/101/odds/1/featured"] = {"featured": {"default": {"choices": [
        {"name": "1", "fractionalValue": "1/2"}, {"name": "X", "fractionalValue": "5/2"}, {"name": "2", "fractionalValue": "4/1"}]}}}
    fake_api.responses.pop("/event/101/odds/55/featured")
    coord._odds_fetched.clear()
    coord._odds_sources.clear()
    await coord.async_refresh()
    await hass.async_block_till_done()
    assert odds_events and odds_events[0].data["outcome"] == "1" and odds_events[0].data["new_odds"] == 1.5

    # goes live, goal with scorer from incidents and a red card
    fake_api.live = [event(101, 1, 2, NOW - 600, "inprogress", 0, 0, 6)]
    coord.events[101]["timestamp"] = NOW - 600
    coord.events[101]["incidents"] = []
    fake_api.responses["/event/101/incidents"] = {"incidents": []}
    await coord.async_refresh()
    await hass.async_block_till_done()
    fake_api.live = [event(101, 1, 2, NOW - 600, "inprogress", 1, 0, 6)]
    fake_api.responses["/event/101/incidents"] = {"incidents": [
        {"incidentType": "goal", "id": 5001, "time": 23, "isHome": True, "homeScore": 1, "awayScore": 0,
         "player": {"shortName": "L. Haraslín"}},
        {"incidentType": "card", "id": 5002, "incidentClass": "red", "time": 30, "isHome": False,
         "player": {"shortName": "T. Holeš"}}]}
    await coord.async_refresh()
    await hass.async_block_till_done()
    goal = [e.data for e in events if e.data["kind"] == "score"]
    assert goal and "L. Haraslín" in goal[-1]["message"]
    assert any(e.data["kind"] == "red_card" and "Holeš" in e.data["title"] for e in events)


SZLH_PAGES = {
    "/sk/stats/tournaments": """
        <h2>Mládež</h2>
        <a href="/sk/stats/home/819/liga-mladsich-ziakov-6-rocnik">Liga mladších žiakov 6.ročník</a>
        <a href="/sk/stats/home/627/1-liga-mladsich-ziakov-6-rocnik">1. liga mladších žiakov 6.ročník</a>
        <h2>Seniori</h2><a href="/sk/stats/home/1131/tipsport-liga">Tipsport liga</a>""",
    "/sk/stats/standings/819/liga-mladsich-ziakov-6-rocnik": """
        <h3>Liga A</h3><table><tr><th>#</th><th>Tím</th><th>Z</th><th>V</th><th>P</th><th>Skóre</th><th>B</th></tr>
        <tr><td>1.</td><td>HC Košice B</td><td>3</td><td>3</td><td>0</td><td>33:7</td><td>18</td></tr>
        <tr><td>4.</td><td>HKM Zvolen</td><td>3</td><td>2</td><td>1</td><td>43:16</td><td>16</td></tr></table>""",
    "/sk/stats/results/819/liga-mladsich-ziakov-6-rocnik": "",  # filled in the test (needs dates relative to now)
}


async def test_szlh_competition_youth_league(hass: HomeAssistant, hass_ws_client, fake_api) -> None:
    from datetime import datetime, timedelta

    from custom_components.ha_sport.szlh import team_id

    soon = datetime.now() + timedelta(days=2)
    past = datetime.now() - timedelta(days=3)
    SZLH_PAGES["/sk/stats/results/819/liga-mladsich-ziakov-6-rocnik"] = f"""
        <table>
        <tr><td>{past:%d. %m. %Y}</td></tr>
        <tr><td>09:00</td><td>HKM Zvolen</td><td>7:2</td><td>HC Košice B</td></tr>
        <tr><td>{soon:%d. %m. %Y}</td></tr>
        <tr><td>10:15</td><td>HK Dukla Trenčín</td><td></td><td>HKM Zvolen</td></tr>
        </table>"""

    async def fake_get(self, path):
        return SZLH_PAGES.get(path)

    with patch("custom_components.ha_sport.szlh.SzlhClient._get", new=fake_get):
        entry = await _setup(hass)
        # options: SZĽH -> search -> select
        result = await hass.config_entries.options.async_init(entry.entry_id)
        result = await hass.config_entries.options.async_configure(result["flow_id"], {"next_step_id": "szlh"})
        assert result["step_id"] == "szlh"
        result = await hass.config_entries.options.async_configure(result["flow_id"], {"search": "6. rocnik"})
        assert result["step_id"] == "szlh_select"
        options = [o["value"] for o in result["data_schema"].schema["selected"].config["options"]]
        assert options == ["819", "627"] or sorted(options) == ["627", "819"]
        result = await hass.config_entries.options.async_configure(result["flow_id"], {"selected": ["819"]})
        assert result["type"] is FlowResultType.CREATE_ENTRY
        comps = entry.options["competitions"]
        assert any(c["id"] == "szlh-819" and c["source"] == "szlh" for c in comps)
        assert any(c["id"] == 172 for c in comps)  # Sofascore competitions kept
        await hass.async_block_till_done()

        # favorite HKM Zvolen (negative id)
        zvolen = team_id("HKM Zvolen")
        hass.config_entries.async_update_entry(
            entry, options={**entry.options, "favorite_teams": [
                *entry.options.get("favorite_teams", entry.data["favorite_teams"]),
                {"id": zvolen, "name": "HKM Zvolen", "sport": "ice-hockey"}]}
        )
        await hass.async_block_till_done()
        coord = entry.runtime_data.coordinator
        assert coord.standings["szlh-819"][0]["rows"][1]["team"] == "HKM Zvolen"
        summary = coord.team_summary(zvolen)
        assert summary["next"]["away"]["name"] == "HKM Zvolen"
        assert summary["form"] == ["W"]
        assert summary["position"]["points"] == 16
        assert not summary["next"]["streams"]

        client = await hass_ws_client(hass)
        await client.send_json({"id": 1, "type": "ha_sport/matches", "competition_id": "szlh-819", "status": "results"})
        msg = await client.receive_json()
        assert msg["success"] and msg["result"]["matches"][0]["home"]["score"] == 7
        await client.send_json({"id": 2, "type": "ha_sport/competition", "competition_id": "szlh-819"})
        msg = await client.receive_json()
        assert msg["result"]["standings"][0]["rows"][0]["points_per_game"] == 6.0
        # sensors of the youth team exist
        assert any(s.attributes.get("team_id") == zvolen for s in hass.states.async_all("sensor"))


async def test_szlh_in_competitions_list(hass: HomeAssistant, fake_api) -> None:
    """SZĽH youth leagues appear directly in the competitions select (setup + options)."""
    fake_api.responses["/sport/ice-hockey/categories"] = {"categories": [{"id": 21, "name": "Slovakia", "alpha2": "SK"}]}
    fake_api.responses["/category/21/unique-tournaments"] = {"groups": [{"uniqueTournaments": [{"id": 900, "name": "Tipsport Liga"}]}]}

    async def fake_get(self, path):
        return SZLH_PAGES.get(path)

    with patch("custom_components.ha_sport.szlh.SzlhClient._get", new=fake_get):
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"sports": ["ice-hockey"], "countries": ["SK"], "base_url": "https://www.sofascore.com/api/v1"}
        )
        assert result["step_id"] == "competitions"
        opts = result["data_schema"].schema["competitions"].config["options"]
        labels = [o["label"] for o in opts]
        assert any("SZĽH · Liga mladších žiakov 6.ročník" in label for label in labels)
        value = next(o["value"] for o in opts if "6.ročník" in o["label"] and "1. liga" not in o["label"])
        # SZĽH is not pre-selected
        marker = next(k for k in result["data_schema"].schema if k == "competitions")
        assert value not in marker.default()
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {"competitions": [value]})
        assert result["step_id"] == "favorites"
        fav_labels = [o["label"] for o in result["data_schema"].schema["favorite_teams"].config["options"]]
        assert any("HKM Zvolen" in label for label in fav_labels)


async def test_szlh_competition_by_link(hass: HomeAssistant, fake_api) -> None:
    pages = {
        "/sk/stats/results/1207/liga-mladsich-ziakov-aa":
            "<title>Súťaže a štatistiky | Liga mladších žiakov AA | Program a výsledky | HockeySlovakia.sk</title>",
    }

    async def fake_get(self, path):
        return pages.get(path)

    with patch("custom_components.ha_sport.szlh.SzlhClient._get", new=fake_get):
        entry = await _setup(hass)
        result = await hass.config_entries.options.async_init(entry.entry_id)
        result = await hass.config_entries.options.async_configure(result["flow_id"], {"next_step_id": "competitions"})
        assert result["step_id"] == "competitions"
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"szlh_link": "nesmysl"}
        )
        assert result["errors"] == {"szlh_link": "szlh_bad_link"}
        current = [c for c in entry.options.get("competitions", entry.data["competitions"])]
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {"competitions": [f"football|CZ|{UT}|Chance Liga"],
             "szlh_link": "https://www.hockeyslovakia.sk/sk/stats/results/1207/liga-mladsich-ziakov-aa"},
        )
        assert result["type"] is FlowResultType.CREATE_ENTRY
        comps = entry.options["competitions"]
        szlh = next(c for c in comps if c.get("source") == "szlh")
        assert szlh["id"] == "szlh-1207" and szlh["name"] == "Liga mladších žiakov AA"
        assert szlh["slug"] == "liga-mladsich-ziakov-aa"
        assert any(c["id"] == UT for c in comps) and current


async def test_szlh_preset_link_prefilled(hass: HomeAssistant, fake_api) -> None:
    async def fake_get(self, path):
        return None

    with patch("custom_components.ha_sport.szlh.SzlhClient._get", new=fake_get):
        entry = await _setup(hass)
        result = await hass.config_entries.options.async_init(entry.entry_id)
        result = await hass.config_entries.options.async_configure(result["flow_id"], {"next_step_id": "competitions"})
        marker = next(k for k in result["data_schema"].schema if k == "szlh_link")
        assert "1207/liga-mladsich-ziakov-aa" in marker.description["suggested_value"]

        # once configured, the field is empty (can be edited/removed in the competitions list)
        hass.config_entries.async_update_entry(entry, options={**entry.options, "competitions": [
            *entry.data["competitions"],
            {"id": "szlh-1207", "szlh_id": 1207, "slug": "liga-mladsich-ziakov-aa", "name": "Liga mladších žiakov AA",
             "sport": "ice-hockey", "country": "SK", "source": "szlh"}]})
        await hass.async_block_till_done()
        result = await hass.config_entries.options.async_init(entry.entry_id)
        result = await hass.config_entries.options.async_configure(result["flow_id"], {"next_step_id": "competitions"})
        marker = next(k for k in result["data_schema"].schema if k == "szlh_link")
        assert marker.description["suggested_value"] == ""


async def test_youth_league_end_to_end(hass: HomeAssistant, hass_ws_client, fake_api) -> None:
    """Liga mladších žiakov AA with HKM Zvolen as favorite: sensors, calendar, reminders."""
    from datetime import datetime, timedelta

    from custom_components.ha_sport.calendar import to_calendar_event
    from custom_components.ha_sport.szlh import TZ, team_id

    now = datetime.now(TZ)
    played = now - timedelta(days=2)
    tomorrow = now + timedelta(days=1)
    later = now + timedelta(days=5)
    pages = {
        "/sk/stats/standings/1207/liga-mladsich-ziakov-aa": """
            <title>Súťaže a štatistiky | Liga mladších žiakov AA | Tabuľky | HockeySlovakia.sk</title>
            <h2>Základná časť</h2>
            <table><thead><tr><th>#</th><th>Tím</th><th>Z</th><th>V</th><th>P</th><th>Skóre</th><th>B</th></tr></thead>
            <tr><td>1.</td><td><a href="/sk/stats/teams/1207/x/team/1/y">HC Košice</a></td><td>3</td><td>3</td><td>0</td><td>33:7</td><td>18</td></tr>
            <tr><td>2.</td><td><a href="/sk/stats/teams/1207/x/team/2/y">HKM Zvolen</a></td><td>3</td><td>2</td><td>1</td><td>43:16</td><td>16</td></tr>
            </table>
            <h2>Najlepší strelci</h2>
            <table><tr><th>Hráč</th><th>G</th></tr><tr><td>NOVÁK, Peter</td><td>9</td></tr><tr><td>KOVÁČ, Ján</td><td>7</td></tr></table>""",
        "/sk/stats/results/1207/liga-mladsich-ziakov-aa": f"""
            <title>Súťaže a štatistiky | Liga mladších žiakov AA | Program a výsledky | HockeySlovakia.sk</title>
            <table>
            <tr><td>{played:%d.%m.}</td></tr>
            <tr><td>10:00</td><td><a href="/sk/stats/teams/1207/x/team/2/y">HKM Zvolen</a></td><td>7:2</td>
                <td><a href="/sk/stats/teams/1207/x/team/1/y">HC Košice</a></td></tr>
            <tr><td>{tomorrow:%d.%m.}</td></tr>
            <tr><td><a href="/sk/stats/teams/1207/x/team/3/y">HK Poprad</a></td><td></td>
                <td><a href="/sk/stats/teams/1207/x/team/2/y">HKM Zvolen</a></td></tr>
            <tr><td>{later:%d.%m.}</td></tr>
            <tr><td>15:30</td><td><a href="/sk/stats/teams/1207/x/team/2/y">HKM Zvolen</a></td><td></td>
                <td><a href="/sk/stats/teams/1207/x/team/4/y">SLOVAN Bratislava - mládež</a></td></tr>
            </table>""",
    }

    async def fake_get(self, path):
        return pages.get(path)

    zvolen = team_id("HKM Zvolen")
    with patch("custom_components.ha_sport.szlh.SzlhClient._get", new=fake_get):
        entry = MockConfigEntry(domain=DOMAIN, title="HA Sport", data={
            **ENTRY_DATA,
            "competitions": [{"id": "szlh-1207", "szlh_id": 1207, "slug": "liga-mladsich-ziakov-aa",
                              "name": "Liga mladších žiakov AA", "sport": "ice-hockey", "country": "SK", "source": "szlh"}],
            "favorite_teams": [{"id": zvolen, "name": "HKM Zvolen", "sport": "ice-hockey"}],
            "notify_before": ["1440", "60"],
        })
        entry.add_to_hass(hass)
        events = async_capture_events(hass, EVENT_NOTIFICATION)
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        coord = entry.runtime_data.coordinator

        # only the real standings table, no player stats
        assert [t["name"] for t in coord.standings["szlh-1207"]] == ["Základná časť"]
        summary = coord.team_summary(zvolen)
        assert summary["position"]["position"] == 2 and summary["position"]["points_per_game"] == 5.33
        assert summary["form"] == ["W"]
        nxt = summary["next"]
        assert nxt["home"]["name"] == "HK Poprad" and nxt["time_known"] is False
        assert [e["away"]["name"] for e in summary["this_week"]] == ["HKM Zvolen", "SLOVAN Bratislava - mládež"]

        # unknown time -> all-day calendar entry, no 60-min reminder (only the day-before one)
        cal = to_calendar_event(nxt)
        assert not hasattr(cal.start, "hour")
        pre = [e.data for e in events if e.data["kind"] == "pre_match"]
        assert all(p["minutes"] == 1440 for p in pre)
        timers = entry.runtime_data.notifier._timers
        assert not any(k.startswith(f"{nxt['id']}:pre:60") for k in timers)
        later_ev = summary["this_week"][1]
        assert any(k == f"{later_ev['id']}:pre:60" for k in timers)

        # sensors and calendar entity work, no Sofascore-only lookups for SZĽH ids
        states = hass.states.async_all()
        assert any(s.attributes.get("team_id") == zvolen and s.attributes.get("opponent") == "HK Poprad" for s in states)
        pos = next(s for s in states if s.attributes.get("points") == 16)
        assert pos.state == "2"
        assert not any(eid < 0 for eid in coord._odds_fetched)

        client = await hass_ws_client(hass)
        await client.send_json({"id": 1, "type": "ha_sport/overview"})
        msg = await client.receive_json()
        assert msg["result"]["competitions"][0]["id"] == "szlh-1207"
        await client.send_json({"id": 2, "type": "ha_sport/team", "team_id": zvolen})
        msg = await client.receive_json()
        assert msg["success"] and msg["result"]["next"]["competition"] == "Liga mladších žiakov AA"
