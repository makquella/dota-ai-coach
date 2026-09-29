"""Advice counts for the opt-in anonymous statistics (app/usage_stats.py)."""

from __future__ import annotations

from app.usage_stats import usage_stats

DAY = 86400
SINCE = 1_800_000_000


def _match(start, advice=(), ignored=()):
    return {
        "match_id": 99,
        "hero": "Juggernaut",
        "start_time": start,
        "analysis": {
            "advice": [
                {"t": t, "dp": dp, "mode": mode, "action": "text"} for t, dp, mode in advice
            ],
            "advice_follow": {
                "urgent": 1,
                "ignored": [{"t": t, "death_t": t + 10} for t in ignored],
            },
        },
    }


def test_counts_advice_and_ignored_warnings_of_the_period_only():
    matches = [
        _match(
            SINCE + 100,
            advice=[
                (300, "LOW_HP_WARNING", "urgent"),
                (500, "LANING_FARM_CHECK", "coaching"),
                (700, "LOW_HP_WARNING", "urgent"),
                (900, "bad kind!", "coaching"),
            ],
            ignored=[700],
        ),
        _match(SINCE + 200),  # analysed, no live advice (an OpenDota-only match)
        _match(SINCE + DAY + 5, advice=[(100, "LOW_HP_WARNING", "urgent")]),  # the next day
        {"start_time": SINCE + 300, "analysis": None},  # not analysed
    ]
    usage = usage_stats(matches, SINCE, SINCE + DAY)
    assert usage == {
        "matches": 2,
        "with_advice": 1,
        "advice": {"LOW_HP_WARNING": 2, "LANING_FARM_CHECK": 1},
        "ignored": {"LOW_HP_WARNING": 1},
    }
    # Nothing that names the match, the hero or the texts.
    assert "99" not in str(usage) and "Juggernaut" not in str(usage) and "text" not in str(usage)


def test_the_usage_endpoint(client):
    body = client.get(f"/player/usage?since={SINCE}&until={SINCE + DAY}").json()
    assert body["usage"] == {"matches": 0, "with_advice": 0, "advice": {}, "ignored": {}}
    assert client.get(f"/player/usage?since={SINCE}&until={SINCE - 1}").status_code == 422
    assert client.get(f"/player/usage?since={SINCE}&until={SINCE + 9 * DAY}").status_code == 422


def test_counts_cover_the_whole_advice_log_not_the_40_cards_shown(tmp_path):
    from match_fixtures import gsi_match_stream

    from app.match_facts import facts_from_timeline
    from app.match_tracker import MatchTracker
    from app.post_match_analysis import analyze_match

    finished = []
    tracker = MatchTracker(tmp_path / "live.json", on_finished=finished.append)
    noted = False
    for payload in gsi_match_stream(death_minutes=(28,)):
        tracker.observe(payload)
        if not noted and payload["map"]["clock_time"] >= 20 * 60:
            noted = True
            for i in range(49):  # more coaching cards than the review shows
                tracker.note_advice(
                    60 + 10 * i, "LANING_FARM_CHECK", "Farm the wave.", "", "coaching"
                )
            # The 50th card, urgent, and the death 10 s later: past the first 40.
            tracker.note_advice(28 * 60 - 10, "LOW_HP_WARNING", "Back off now.", "", "urgent")
    analysis = analyze_match(facts_from_timeline(finished[0]))
    assert len(analysis["advice"]) == 40
    assert analysis["advice_counts"] == {
        "shown": {"LANING_FARM_CHECK": 49, "LOW_HP_WARNING": 1},
        "ignored": {"LOW_HP_WARNING": 1},
    }
    usage = usage_stats([{"start_time": SINCE + 60, "analysis": analysis}], SINCE, SINCE + DAY)
    assert usage["advice"] == {"LANING_FARM_CHECK": 49, "LOW_HP_WARNING": 1}
    assert usage["ignored"] == {"LOW_HP_WARNING": 1}
