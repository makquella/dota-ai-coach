"""The post-match review of a support: the save item, and wards counted from GSI."""

from __future__ import annotations

from match_fixtures import gsi_match_stream

from app.analysis_texts import render_finding
from app.match_facts import facts_from_timeline
from app.match_tracker import MatchTracker
from app.post_match_analysis import _support_items, analyze_match


def _facts(items, minutes=35):
    return {
        "duration": minutes * 60,
        "items_log": [{"t": t, "item": item} for t, item in items],
    }


def _ids(findings):
    return [f["id"] for f in findings]


def test_a_save_item_on_time():
    findings = []
    block = _support_items(
        _facts([(300, "item_tranquil_boots"), (13 * 60, "item_glimmer_cape")]), findings
    )
    assert block["save_item"] == {"t": 13 * 60, "item": "Glimmer Cape"}
    assert block["score"] == 100
    assert _ids(findings) == ["save_item_fast"]
    text = render_finding(findings[0], "uk")
    assert text["text"].startswith("Glimmer Cape уже до 13:00")


def test_a_late_save_item_and_its_score():
    findings = []
    # OpenDota's purchase log names items without the "item_" prefix.
    block = _support_items(_facts([(25 * 60, "force_staff"), (30 * 60, "glimmer_cape")]), findings)
    assert block["save_item"] == {"t": 25 * 60, "item": "Force Staff"}
    assert block["score"] == 50  # 100 − 10 minutes over × 5
    assert _ids(findings) == ["save_item_slow"]
    assert [row["item"] for row in block["save_items"]] == ["Force Staff", "Glimmer Cape"]


def test_no_save_item_in_a_long_game_but_not_in_a_short_one():
    findings = []
    block = _support_items(_facts([(300, "item_arcane_boots")], minutes=40), findings)
    assert block["save_item"] is None and block["score"] == 20
    assert _ids(findings) == ["save_item_missing"]
    assert render_finding(findings[0], "en")["drill"].startswith("After boots and wards")
    short = []
    assert _support_items(_facts([(300, "item_arcane_boots")], minutes=20), short) is None
    assert short == []
    assert _support_items({"duration": 40 * 60, "items_log": []}, []) is None


def _wards(clock):
    """Two wards at 1:00, one placed at 2:00, two more bought at 5:00, two placed
    at 8:00, the last one lost to a death at 20:00 (not placed)."""
    if clock < 60:
        return 0
    if clock < 120:
        return 2
    if clock < 300:
        return 1
    if clock < 480:
        return 3
    if clock < 20 * 60:
        return 1
    return 0


def test_wards_placed_are_counted_from_the_inventory(tmp_path):
    finished = []
    tracker = MatchTracker(tmp_path / "live.json", on_finished=finished.append)
    for payload in gsi_match_stream(death_minutes=(20,), lh_per_minute=1.0):
        payload["hero"]["name"] = "npc_dota_hero_lion"
        clock = payload["map"]["clock_time"]
        payload["items"] = {"slot0": {"name": "item_tango"}}
        charges = _wards(clock)
        if charges:
            payload["items"]["slot1"] = {"name": "item_ward_observer", "charges": charges}
        tracker.observe(payload)
    facts = facts_from_timeline(finished[0])
    assert facts["obs_placed"] == 3
    analysis = analyze_match(facts)
    assert analysis["role"] == "support"
    assert analysis["sections"]["vision"]["obs_placed"] == 3
