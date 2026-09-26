"""Linked player, whole-match recording, OpenDota sync and post-match reviews."""

from __future__ import annotations

import re

import pytest
from match_fixtures import (
    MATCH_ID,
    ME,
    ME_STEAM64,
    FakeOpenDota,
    gsi_match_stream,
    opendota_match,
    recent_matches,
)

from app.analysis_texts import FINDINGS, render_analysis
from app.career_analysis import analyze_career
from app.match_facts import facts_from_opendota, facts_from_timeline, merge_facts
from app.match_tracker import MatchTracker
from app.opendota import summary_from_match, trim_match
from app.player_api import PLAYER_SERVICE
from app.player_service import PlayerService
from app.post_match_analysis import analyze_match
from app.steam_ids import SteamIdError, parse_account_id

# --- Steam ids -------------------------------------------------------------------


@pytest.mark.parametrize(
    "value",
    [
        "52079950",
        ME_STEAM64,
        f"https://steamcommunity.com/profiles/{ME_STEAM64}/",
        "https://www.opendota.com/players/52079950",
        "https://www.dotabuff.com/players/52079950/matches",
        "[U:1:52079950]",
        "STEAM_0:0:26039975",
        " 52079950 ",
    ],
)
def test_parse_account_id_formats(value):
    assert parse_account_id(value) == ME


@pytest.mark.parametrize(
    ("value", "code"),
    [
        ("", "empty"),
        ("https://steamcommunity.com/id/someone", "vanity_url"),
        ("hello", "unrecognized"),
        ("0", "out_of_range"),
    ],
)
def test_parse_account_id_errors(value, code):
    with pytest.raises(SteamIdError) as error:
        parse_account_id(value)
    assert error.value.code == code


# --- live match tracker ------------------------------------------------------------


def test_tracker_records_a_whole_match(tmp_path):
    finished = []
    tracker = MatchTracker(tmp_path / "live.json", on_finished=finished.append)
    for payload in gsi_match_stream(death_minutes=(7, 18), win=True):
        tracker.observe(payload)

    assert len(finished) == 1
    timeline = finished[0]
    assert timeline["match_id"] == MATCH_ID
    assert timeline["account_id"] == ME
    assert timeline["steam_id64"] == ME_STEAM64
    assert timeline["hero"] == "Juggernaut"
    assert timeline["finished"] is True
    assert timeline["win"] is True
    assert [d["t"] for d in timeline["deaths"]] == [7 * 60, 18 * 60]
    assert timeline["deaths"][0]["gold"] == 1800
    assert [i["item"] for i in timeline["items"]][:3] == [
        "item_tango",
        "item_power_treads",
        "item_bfury",
    ]
    times = [s["t"] for s in timeline["samples"]]
    assert times[0] == 0 and all(b - a >= 15 for a, b in zip(times, times[1:], strict=False))
    assert timeline["scores"]["radiant"] > 0
    assert not (tmp_path / "live.json").exists()
    assert not any(key.startswith("_") for key in timeline)


def test_tracker_survives_a_restart_mid_match(tmp_path):
    stream = gsi_match_stream()
    first = MatchTracker(tmp_path / "live.json")
    for payload in stream[: len(stream) // 2]:
        first.observe(payload)
    first.flush()

    finished = []
    second = MatchTracker(tmp_path / "live.json", on_finished=finished.append)
    assert second.current()["match_id"] == MATCH_ID
    for payload in stream[len(stream) // 2 :]:
        second.observe(payload)
    assert len(finished) == 1
    assert finished[0]["samples"][0]["t"] == 0


def test_tracker_finishes_stale_match_and_skips_short_games(tmp_path):
    now = [0.0]
    finished = []
    tracker = MatchTracker(
        tmp_path / "live.json", on_finished=finished.append, clock=lambda: now[0]
    )
    # A 3-minute game (abandoned): no review.
    for payload in gsi_match_stream(minutes=3)[:-1]:
        tracker.observe(payload)
    now[0] += 11 * 60
    tracker.check_stale()
    assert finished == []
    assert tracker.current() is None

    for payload in gsi_match_stream(match_id=MATCH_ID + 1, minutes=20)[:-1]:
        tracker.observe(payload)
    now[0] += 11 * 60
    tracker.check_stale()
    assert len(finished) == 1
    assert finished[0]["end_reason"] == "stale"
    assert finished[0]["win"] is None


def test_tracker_ignores_demo_and_lobby_ids(tmp_path):
    tracker = MatchTracker(tmp_path / "live.json")
    payload = gsi_match_stream()[100]
    payload["map"]["matchid"] = "gsi_juggernaut_live_lane_test"
    tracker.observe(payload)
    assert tracker.current() is None


# --- analysis ------------------------------------------------------------------------


def _analysis(match, lang="en"):
    facts = facts_from_opendota(trim_match(match, ME))
    return render_analysis(analyze_match(facts), lang)


def test_good_parsed_match_is_praised():
    analysis = _analysis(opendota_match(good=True))
    assert analysis["headline"]["grade"] == "A"
    assert analysis["role"] == "core"
    ids = {f["id"] for f in analysis["strengths"]}
    assert {"lh10_great", "gpm_high", "deaths_low"} <= ids
    assert not [f for f in analysis["improvements"] if f["severity"] >= 3]


def test_bad_parsed_match_names_the_problems_with_numbers():
    analysis = _analysis(opendota_match(good=False), lang="ru")
    assert analysis["headline"]["grade"] == "D"
    ids = [f["id"] for f in analysis["improvements"]]
    assert "gpm_low" in ids
    assert "core_item_slow" in ids
    assert "farm_stall" in ids
    assert analysis["focus"] == ids[:3]
    gpm = next(f for f in analysis["improvements"] if f["id"] == "gpm_low")
    assert "390" in gpm["text"] and "88%" in gpm["text"] and gpm["drill"]
    stall = next(f for f in analysis["improvements"] if f["id"] == "farm_stall")
    assert "С 15 по 22-ю минуту" in stall["text"]
    assert analysis["series"]["last_hits"][10] < analysis["series"]["last_hits_target"][10]
    killers = [m["killer"] for m in analysis["moments"] if m["type"] == "death"]
    assert killers[0] == "Shadow Fiend"


def test_unparsed_match_still_gets_a_review_without_timelines():
    analysis = _analysis(opendota_match(good=False, parsed=False))
    assert analysis["parsed"] is False
    assert "laning" not in analysis["sections"]
    assert {"farm", "survival", "fights"} <= set(analysis["sections"])


def test_gsi_timeline_review_and_merge_with_opendota(tmp_path):
    finished = []
    tracker = MatchTracker(tmp_path / "live.json", on_finished=finished.append)
    for payload in gsi_match_stream(lh_per_minute=3.0, death_minutes=(3, 6, 20)):
        tracker.observe(payload)
    gsi = facts_from_timeline(finished[0])
    assert gsi["lh_t"][10] == 30
    assert gsi["kill_participation"] is not None
    analysis = analyze_match(gsi)
    ids = {f["id"] for f in analysis["improvements"]}
    assert {"lh10_low", "lane_deaths", "death_with_gold"} <= ids

    od = facts_from_opendota(trim_match(opendota_match(good=False, my_deaths=[180, 360, 1200]), ME))
    merged = merge_facts(od, gsi)
    assert merged["sources"] == ["gsi", "opendota"]
    # OpenDota knows the killer, GSI the unspent gold at that death.
    assert merged["deaths_log"][0]["killer"] == "Shadow Fiend"
    assert merged["deaths_log"][0]["gold"] == 1800


def test_every_finding_has_both_languages_and_formats_cleanly():
    produced = set()
    for match in (
        opendota_match(good=True),
        opendota_match(good=False),
        opendota_match(good=False, parsed=False),
    ):
        for lang in ("ru", "en"):
            analysis = _analysis(match, lang)
            for finding in analysis["strengths"] + analysis["improvements"]:
                produced.add(finding["id"])
                for text in (finding["title"], finding["text"], finding.get("drill") or ""):
                    assert "{" not in text and text.strip() != "—", (finding["id"], text)
                assert not re.search(r"\bNone\b", finding["text"]), finding
    assert produced
    for finding_id, langs in FINDINGS.items():
        assert set(langs) == {"ru", "en"}, finding_id
        assert set(langs["ru"]) == set(langs["en"]), finding_id


# --- career ---------------------------------------------------------------------------


def test_career_trend_heroes_and_recurring_problems():
    matches = []
    for index in range(20):
        good = index < 10  # recent 10 good, previous 10 bad -> improving
        match = opendota_match(good=good, match_id=MATCH_ID - index)
        trimmed = trim_match(match, ME)
        summary = summary_from_match(trimmed)
        summary["match_id"] = MATCH_ID - index
        summary["start_time"] = 1790000000 - index * 3600
        summary["analysis"] = analyze_match(facts_from_opendota(trimmed))
        matches.append(summary)
    career = analyze_career(matches, "ru")
    assert career["matches"] == 20 and career["winrate"] == 50
    assert career["trend"]["gpm"]["direction"] == "up" and career["trend"]["gpm"]["better"]
    assert career["trend"]["deaths"]["direction"] == "down" and career["trend"]["deaths"]["better"]
    assert career["heroes"][0]["hero"] == "Juggernaut"
    recurring = {item["id"]: item for item in career["recurring"]}
    assert recurring["gpm_low"]["count"] == 10 and recurring["gpm_low"]["of"] == 20
    assert career["focus_plan"] and all(item["drill"] for item in career["focus_plan"])
    assert career["streak"] == {"win": True, "length": 10}
    assert len(career["series"]) == 20 and career["series"][-1]["match_id"] == MATCH_ID


# --- service + API --------------------------------------------------------------------


def _service(tmp_path, client):
    PLAYER_SERVICE.configure(tmp_path / "svc", client=client, auto_start=False)
    return PLAYER_SERVICE


def test_gsi_links_the_player_and_reviews_the_match(client, tmp_path):
    fake = FakeOpenDota(matches={MATCH_ID: opendota_match(good=False)})
    service = _service(tmp_path, fake)
    assert client.get("/player").json()["linked"] is False

    for payload in gsi_match_stream(win=False):
        assert client.post("/gsi", json=payload).status_code == 200

    status = client.get("/player").json()
    assert status["linked"] and status["account_id"] == ME and status["source"] == "gsi"
    assert status["last_review"]["match_id"] == MATCH_ID
    rows = client.get("/player/matches").json()["items"]
    assert rows[0]["match_id"] == MATCH_ID and rows[0]["win"] is False
    assert rows[0]["sources"] == ["gsi"] and rows[0]["has_timeline"]

    detail = client.get(f"/player/matches/{MATCH_ID}?lang=ru").json()
    assert detail["parse_status"] == "waiting_opendota"
    assert detail["analysis"]["lang"] == "ru" and detail["analysis"]["sources"] == ["gsi"]

    # After the delay the worker fetches OpenDota and rebuilds the review.
    service.jobs.run_pending(until=float("inf"))
    detail = client.get(f"/player/matches/{MATCH_ID}?lang=ru").json()
    assert detail["sources"] == ["gsi", "opendota"]
    assert detail["parse_status"] == "parsed"
    assert detail["analysis"]["parsed"] is True
    assert len(detail["scoreboard"]) == 10 and sum(r["me"] for r in detail["scoreboard"]) == 1


def test_unparsed_match_requests_a_replay_parse(tmp_path):
    fake = FakeOpenDota(matches={MATCH_ID: opendota_match(parsed=False)})
    service = PlayerService(tmp_path, client=fake, auto_start=False)
    service.link(str(ME))
    service.fetch_match(MATCH_ID, request_parse=True)
    service.jobs.run_pending()
    assert fake.parse_requests == [MATCH_ID]
    assert service.store.get_match(ME, MATCH_ID)["parse_status"] == "parsing"
    # The replay is parsed now: the next poll upgrades the review.
    fake.matches[MATCH_ID] = opendota_match(parsed=True)
    service.jobs.run_pending(until=float("inf"))
    record = service.store.get_match(ME, MATCH_ID)
    assert record["parse_status"] == "parsed" and record["analysis"]["parsed"] is True
    assert fake.parse_requests == [MATCH_ID]


def test_link_sync_and_career_endpoints(client, tmp_path):
    recent = recent_matches(15)
    fake = FakeOpenDota(
        matches={
            row["match_id"]: opendota_match(good=row["radiant_win"], match_id=row["match_id"])
            for row in recent
        },
        recent=recent,
    )
    service = _service(tmp_path, fake)

    bad = client.post("/player/link", json={"steam": "steamcommunity.com/id/me"})
    assert bad.status_code == 400 and bad.json()["code"] == "vanity_url"

    linked = client.post(
        "/player/link", json={"steam": f"https://steamcommunity.com/profiles/{ME_STEAM64}"}
    ).json()
    assert linked["linked"] and linked["account_id"] == ME and linked["source"] == "manual"
    service.jobs.run_pending(until=float("inf"))

    status = client.get("/player").json()
    assert status["sync"]["state"] == "done" and status["player"]["persona_name"] == "Me"
    table = client.get("/player/matches?limit=20").json()
    assert table["total"] == 15 and len(table["items"]) == 15
    assert table["items"][0]["match_id"] == MATCH_ID
    reviewed = [row for row in table["items"] if row["has_analysis"]]
    assert len(reviewed) == 12

    career = client.get("/player/career?lang=ru").json()
    assert career["linked"] and career["matches"] == 15 and career["analyzed"] == 12
    assert career["recurring"] and career["recurring"][0]["text"].startswith("В ")

    assert client.get("/player/matches/1").status_code == 404
    assert client.delete("/player").json()["linked"] is False


def test_other_account_in_gsi_is_offered_not_switched(client, tmp_path):
    _service(tmp_path, None)
    client.post("/player/link", json={"steam": "12345"})
    payload = gsi_match_stream()[50]
    client.post("/gsi", json=payload)
    status = client.get("/player").json()
    assert status["account_id"] == 12345
    assert status["detected"]["account_id"] == ME
    assert client.post("/player/link-detected").json()["account_id"] == ME


def test_last_review_belongs_to_the_linked_account(client, tmp_path):
    service = _service(tmp_path, None)
    client.post("/player/link", json={"steam": "12345"})
    # Someone else plays on this PC: their match is stored under their account.
    for payload in gsi_match_stream():
        client.post("/gsi", json=payload)
    assert service.store.get_match(ME, MATCH_ID) is not None
    assert client.get("/player").json()["last_review"] is None
    client.post("/player/link-detected")
    assert client.get("/player").json()["last_review"]["match_id"] == MATCH_ID


def test_sync_skips_bot_practice_and_custom_lobbies(client, tmp_path):
    recent = recent_matches(6)
    recent[1]["lobby_type"] = 4  # bots
    recent[2]["lobby_type"] = 1  # practice
    recent[3]["lobby_type"] = 8  # 1v1 mid
    service = _service(tmp_path, FakeOpenDota(recent=recent))
    client.post("/player/link", json={"steam": str(ME)})
    service.jobs.run_pending(until=float("inf"))
    ids = {row["match_id"] for row in client.get("/player/matches").json()["items"]}
    assert ids == {recent[0]["match_id"], recent[4]["match_id"], recent[5]["match_id"]}


def test_empty_path_env_means_default(monkeypatch, tmp_path):
    from app.config import path_from_env

    monkeypatch.setenv("SOME_DIR", "  ")
    assert path_from_env("SOME_DIR", tmp_path / "x") == tmp_path / "x"
    monkeypatch.setenv("SOME_DIR", str(tmp_path / "y"))
    assert path_from_env("SOME_DIR", tmp_path / "x") == tmp_path / "y"


def test_player_endpoints_work_offline(client, tmp_path):
    _service(tmp_path, None)
    client.post("/player/link", json={"steam": str(ME)})
    assert client.post("/player/sync").json()["opendota"] is False
    assert client.get("/player/matches").json()["items"] == []
    assert client.get("/player/career").json()["matches"] == 0
