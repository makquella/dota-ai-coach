"""Match map: positions from GSI and OpenDota, death sides, the enemy-half rule."""

from __future__ import annotations

from match_fixtures import MATCH_ID, ME, FakeOpenDota, gsi_match_stream, opendota_match

from app.analysis_texts import render_finding
from app.map_analysis import MAP_CENTER, analyze_map, map_side
from app.match_facts import facts_from_opendota
from app.opendota import trim_match
from app.player_api import PLAYER_SERVICE


def _abs(x: int, y: int) -> tuple[int, int]:
    return x + MAP_CENTER, y + MAP_CENTER


def test_sides_follow_the_team():
    radiant_base, dire_base, river = _abs(-6000, -6000), _abs(6000, 6000), _abs(-3000, 3200)
    assert map_side(*radiant_base, True) == "own"
    assert map_side(*dire_base, True) == "enemy"
    assert map_side(*radiant_base, False) == "enemy"
    assert map_side(*dire_base, False) == "own"
    assert map_side(*river, True) == "river"


def test_gsi_match_records_the_path_and_where_each_death_happened(client):
    for payload in gsi_match_stream(positions=True, win=False):
        client.post("/gsi", json=payload)
    detail = client.get(f"/player/matches/{MATCH_ID}?lang=uk").json()
    game_map = detail["analysis"]["map"]
    assert [(d["t"], d["side"]) for d in game_map["deaths"]] == [
        (420, "own"),
        (1080, "enemy"),
        (1140, "enemy"),
        (1200, "enemy"),
    ]
    assert game_map["deaths"][0]["y"] == -6300 + MAP_CENTER  # last alive position, in the lane
    assert game_map["deaths_by_side"] == {"own": 1, "river": 0, "enemy": 3}
    assert 100 < len(game_map["path"]) <= 400
    assert game_map["is_radiant"] is True and game_map["wards"] == []


def test_most_late_deaths_on_the_enemy_half_is_a_finding():
    deaths = [
        {"t": 400, "x": 18000, "y": 10000},  # laning: not counted
        {"t": 900, "x": 21000, "y": 20500},
        {"t": 1300, "x": 20000, "y": 21000},
        {"t": 1900, "x": 12000, "y": 11000},
        {"t": 2100, "x": 22000, "y": 19000},
    ]
    block, findings = analyze_map({"is_radiant": True, "deaths_log": deaths})
    assert block["deaths_by_side"] == {"own": 2, "river": 0, "enemy": 3}
    assert [(f["id"], f["params"]) for f in findings] == [
        ("deaths_enemy_half", {"count": 3, "total": 4})
    ]
    text = render_finding(findings[0], "uk")
    assert text["text"].startswith("3 з 4 смертей після 10-ї хвилини")
    # Dire: the same spots are its own half.
    assert analyze_map({"is_radiant": False, "deaths_log": deaths})[1] == []


def test_no_positions_no_map():
    assert analyze_map({"is_radiant": True, "deaths_log": [{"t": 900}]}) == (None, [])


def test_parsed_replay_gives_wards_and_lane_position(client, tmp_path):
    match = opendota_match()
    me = next(p for p in match["players"] if p["account_id"] == ME)
    me["obs_log"] = [{"time": 130, "x": 118.5, "y": 110.0}, {"time": 900, "x": 150, "y": 90}]
    me["sen_log"] = [{"time": 610, "x": 131, "y": 124}]
    me["lane_pos"] = {"150": {"80": 12, "82": 30}, "10": {"10": 5}}
    facts = facts_from_opendota(trim_match(match, ME))
    assert facts["wards"] == [
        {"t": 130, "x": 15168, "y": 14080, "kind": "obs"},
        {"t": 610, "x": 16768, "y": 15872, "kind": "sen"},
        {"t": 900, "x": 19200, "y": 11520, "kind": "obs"},
    ]
    block, _ = analyze_map(facts)
    # Off-map cells (10, 10) are dropped; the busiest cell comes first.
    assert block["lane"] == [[19200, 10496, 30], [19200, 10240, 12]]
    assert [w["kind"] for w in block["wards"]] == ["obs", "sen", "obs"]

    PLAYER_SERVICE.configure(
        tmp_path / "svc", client=FakeOpenDota(matches={MATCH_ID: match}), auto_start=False
    )
    client.post("/player/link", json={"steam": str(ME)})
    PLAYER_SERVICE.fetch_match(MATCH_ID, request_parse=False)
    PLAYER_SERVICE.jobs.run_pending(until=float("inf"))
    detail = client.get(f"/player/matches/{MATCH_ID}?lang=en").json()
    assert len(detail["analysis"]["map"]["wards"]) == 3
