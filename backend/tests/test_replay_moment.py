"""«Watch this moment»: the recording keeps the replay offset of the match clock."""

from __future__ import annotations

from match_fixtures import gsi_match_stream

from app.match_facts import facts_from_timeline, merge_facts
from app.match_tracker import MatchTracker
from app.post_match_analysis import analyze_match


def test_a_recorded_match_knows_its_replay_offset(tmp_path):
    finished = []
    tracker = MatchTracker(tmp_path / "live.json", on_finished=finished.append)
    for payload in gsi_match_stream(minutes=12):
        tracker.observe(payload)
    timeline = finished[0]
    assert timeline["clock_offset"] == 90  # the fixture's game_time - clock_time
    facts = facts_from_timeline(timeline)
    assert analyze_match(facts)["replay"] == {"clock_offset": 90, "tick_rate": 30}
    # Merged with OpenDota (which has no offset), the recording's one stays.
    opendota = {**facts, "sources": ["opendota"], "clock_offset": None}
    assert merge_facts(opendota, facts)["clock_offset"] == 90


def test_an_opendota_only_match_has_no_replay_block():
    facts = facts_from_timeline({"match_id": 1, "samples": [], "duration": 1800})
    assert analyze_match(facts)["replay"] is None
