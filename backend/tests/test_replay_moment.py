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


def test_the_review_compares_with_the_best_match_on_the_hero(client, tmp_path):
    from match_fixtures import ME, FakeOpenDota, opendota_match, recent_matches

    from app.player_api import PLAYER_SERVICE

    recent = recent_matches(8)
    fake = FakeOpenDota(
        matches={
            row["match_id"]: opendota_match(good=row["radiant_win"], match_id=row["match_id"])
            for row in recent
        },
        recent=recent,
    )
    PLAYER_SERVICE.configure(tmp_path / "svc", client=fake, auto_start=False)
    client.post("/player/link", json={"steam": str(ME)})
    PLAYER_SERVICE.jobs.run_pending(until=float("inf"))
    rows = [r for r in PLAYER_SERVICE.store.matches_for_career(ME, limit=20) if r.get("analysis")]
    scores = {r["match_id"]: r["analysis"]["headline"]["score"] for r in rows}
    worst = min(scores, key=scores.get)
    best = max(scores, key=scores.get)
    detail = client.get(f"/player/matches/{worst}?lang=ru").json()
    compare = detail["best_on_hero"]
    assert compare["score"] == scores[best] and compare["match_id"] == best
    assert len(compare["series"]["last_hits"]) > 2
    top = client.get(f"/player/matches/{best}?lang=ru").json()["best_on_hero"]
    assert top["self_best"] is True and top["of"] == len(rows)
