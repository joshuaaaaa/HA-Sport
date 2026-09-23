"""Parser tests for HockeySlovakia.sk pages (synthetic HTML in the site's style)."""
from custom_components.ha_sport.szlh import (
    parse_matches,
    parse_standings,
    parse_tournaments,
    team_id,
)

TOURNAMENTS = """
<html><body>
<h2>Seniori</h2>
<a href="/sk/stats/home/1131/tipsport-liga">Tipsport liga</a>
<h2>Mládež</h2>
<ul>
 <li><a href="/sk/stats/home/819/liga-mladsich-ziakov-6-rocnik">Liga mladších žiakov 6.ročník</a></li>
 <li><a href="/sk/stats/standings/819/liga-mladsich-ziakov-6-rocnik">Tabuľky</a></li>
 <li><a href="/sk/stats/home/627/1-liga-mladsich-ziakov-6-rocnik">1. liga mladších žiakov 6.ročník</a></li>
</ul>
<a href="/sk/article/nieco">Článok</a>
</body></html>
"""

STANDINGS = """
<h3>Skupina Východ</h3>
<table>
 <thead><tr><th>#</th><th>Tím</th><th>Z</th><th>V</th><th>VP</th><th>PP</th><th>P</th><th>Skóre</th><th>B</th></tr></thead>
 <tbody>
  <tr><td>1.</td><td><a href="/sk/team/1">HC Košice B</a></td><td>3</td><td>3</td><td>0</td><td>0</td><td>0</td><td>33:7</td><td>18</td></tr>
  <tr><td>2.</td><td><a href="/sk/team/2">HK ŠKP Poprad</a></td><td>3</td><td>2</td><td>1</td><td>0</td><td>0</td><td>29:6</td><td>17</td></tr>
 </tbody>
</table>
<h3>Skupina Stred</h3>
<table>
 <tr><th>Por.</th><th>Družstvo</th><th>Zápasy</th><th>Výhry</th><th>Prehry</th><th>Skóre</th><th>Body</th></tr>
 <tr><td>1</td><td>HKM Zvolen</td><td>3</td><td>2</td><td>1</td><td>43:16</td><td>16</td></tr>
 <tr><td>2</td><td>HC 05 Banská Bystrica</td><td>3</td><td>1</td><td>2</td><td>20:22</td><td>9</td></tr>
</table>
"""

RESULTS = """
<h3>Základná časť</h3>
<table>
 <tr><td colspan="5">So 27. 9. 2026</td></tr>
 <tr><td>09:00</td><td><a href="/sk/team/3">HKM Zvolen</a></td><td>7:2</td><td><a href="/sk/team/4">HC Košice B</a></td><td>Detail</td></tr>
 <tr><td>11:30</td><td>HK ŠKP Poprad</td><td>4:5 pp</td><td>HK Dukla Trenčín</td><td>Detail</td></tr>
 <tr><td colspan="5">Ne 4. 10. 2026</td></tr>
 <tr><td>10:15</td><td>HK Dukla Trenčín</td><td></td><td>HKM Zvolen</td><td></td></tr>
 <tr><td>12. 10. 2026 16:45</td><td>Slovan Bratislava - HKM Zvolen</td><td></td></tr>
</table>
"""


def test_tournaments():
    items = parse_tournaments(TOURNAMENTS)
    by_id = {t["id"]: t for t in items}
    assert by_id[819]["name"] == "Liga mladších žiakov 6.ročník"
    assert by_id[819]["slug"] == "liga-mladsich-ziakov-6-rocnik"
    assert by_id[819]["group"] == "Mládež"
    assert by_id[1131]["group"] == "Seniori"
    assert 627 in by_id and len(items) == 3


def test_standings_by_header_names():
    tables = parse_standings(STANDINGS)
    assert [t["name"] for t in tables] == ["Skupina Východ", "Skupina Stred"]
    kos = tables[0]["rows"][0]
    assert kos["team"] == "HC Košice B" and kos["points"] == 18 and kos["scores_for"] == 33 and kos["played"] == 3
    assert tables[0]["rows"][1]["ot_wins"] == 1
    zv = tables[1]["rows"][0]
    assert zv["team"] == "HKM Zvolen" and zv["points"] == 16 and zv["losses"] == 1 and zv["points_per_game"] == 5.33
    assert zv["team_id"] == team_id("HKM Zvolen") < 0


def test_matches():
    comp = {"id": "szlh-819", "name": "Liga mladších žiakov 6.ročník"}
    events = parse_matches(RESULTS, comp)
    assert len(events) == 4
    first = events[0]
    assert first["home"]["name"] == "HKM Zvolen" and first["away"]["name"] == "HC Košice B"
    assert (first["home"]["score"], first["away"]["score"]) == (7, 2) and first["status"] == "finished"
    assert first["start"].startswith("2026-09-27T09:00")
    assert events[1]["status_text"] == "Po prodloužení" and events[1]["winner"] == 2
    upcoming = events[2]
    assert upcoming["status"] == "notstarted" and upcoming["home"]["name"] == "HK Dukla Trenčín"
    assert upcoming["home"]["id"] == team_id("HK Dukla Trenčín")
    split = events[3]
    assert split["home"]["name"] == "Slovan Bratislava" and split["away"]["name"] == "HKM Zvolen"
    assert split["start"].startswith("2026-10-12T16:45")
    # ids are stable
    assert parse_matches(RESULTS, comp)[0]["id"] == first["id"]


def test_competition_url_and_name():
    from custom_components.ha_sport.szlh import competition_name, parse_competition_url

    url = "https://www.hockeyslovakia.sk/sk/stats/results/1207/liga-mladsich-ziakov-aa"
    assert parse_competition_url(url) == (1207, "liga-mladsich-ziakov-aa")
    assert parse_competition_url("https://www.hockeyslovakia.sk/sk/stats/results-date/1141/liga-mladsich-ziakov-aa?x=1") == (1141, "liga-mladsich-ziakov-aa")
    assert parse_competition_url("1207") == (1207, "")
    assert parse_competition_url("https://example.com/foo") is None
    html = "<html><head><title>Súťaže a štatistiky | Liga mladších žiakov AA | Program a výsledky | HockeySlovakia.sk</title></head></html>"
    assert competition_name(html) == "Liga mladších žiakov AA"
    assert competition_name("<html></html>", "liga-mladsich-ziakov-aa") == "Liga mladsich ziakov aa"


def test_matches_prefer_team_links():
    html = """
    <table>
     <tr><td>So 27. 9. 2026</td></tr>
     <tr><td>09:00</td><td>Zimný štadión Zvolen</td>
         <td><a href="/sk/stats/teams/1207/liga-mladsich-ziakov-aa/team/667196/mhk-ruzomberok">MHK Ružomberok</a></td>
         <td>3:4</td>
         <td><a href="/sk/stats/teams/1207/liga-mladsich-ziakov-aa/team/667179/slovan">SLOVAN Bratislava - mládež</a></td></tr>
    </table>"""
    ev = parse_matches(html, {"id": "szlh-1207", "name": "Liga mladších žiakov AA"})[0]
    assert ev["home"]["name"] == "MHK Ružomberok" and ev["away"]["name"] == "SLOVAN Bratislava - mládež"
    assert (ev["home"]["score"], ev["away"]["score"]) == (3, 4)


def test_short_dates_scores_and_overdue():
    from datetime import datetime

    from custom_components.ha_sport.szlh import TZ, find_date

    now = datetime(2026, 12, 20, 12, 0, tzinfo=TZ)
    assert find_date(" So 27.09.", now) == (2026, 9, 27)
    assert find_date(" Ne 3. 1.", now) == (2027, 1, 3)  # season crosses new year
    assert find_date("27. 9. 2025", now) == (2025, 9, 27)
    html = """
    <table>
     <tr><td>So 13.12.</td></tr>
     <tr><td>09:00</td><td>HKM Zvolen</td><td>12:10</td><td>HC Košice</td></tr>
     <tr><td>Ne 14.12.</td></tr>
     <tr><td>HKM Zvolen</td><td></td><td>HK Poprad</td></tr>
     <tr><td>Po 22.12. 17:30</td><td>HK Poprad</td><td></td><td>HKM Zvolen</td></tr>
    </table>"""
    events = parse_matches(html, {"id": "szlh-1207", "name": "Liga mladších žiakov AA"}, now)
    assert len(events) == 3
    first, overdue, future = events
    assert first["start"].startswith("2026-12-13T09:00")
    assert (first["home"]["score"], first["away"]["score"]) == (12, 10)
    assert overdue["time_known"] is False and overdue["status_text"] == "Výsledek zatím nezapsán"
    assert future["time_known"] is True and future["start"].startswith("2026-12-22T17:30")
    assert future["status_text"] == "Nezačalo"


def test_standings_skip_player_tables():
    html = """
    <h3>Tabuľka</h3>
    <table><tr><th>#</th><th>Tím</th><th>Z</th><th>Skóre</th><th>B</th></tr>
      <tr><td>1.</td><td>HKM Zvolen</td><td>3</td><td>43:16</td><td>16</td></tr>
      <tr><td>2.</td><td>HC Košice</td><td>3</td><td>33:7</td><td>15</td></tr></table>
    <h3>Najlepší strelci</h3>
    <table><tr><th>#</th><th>Hráč</th><th>G</th><th>A</th><th>B</th></tr>
      <tr><td>1.</td><td>NOVÁK, Peter</td><td>9</td><td>4</td><td>13</td></tr>
      <tr><td>2.</td><td>KOVÁČ, Ján</td><td>7</td><td>5</td><td>12</td></tr></table>
    """
    tables = parse_standings(html)
    assert [t["name"] for t in tables] == ["Tabuľka"]
    assert [r["team"] for r in tables[0]["rows"]] == ["HKM Zvolen", "HC Košice"]
