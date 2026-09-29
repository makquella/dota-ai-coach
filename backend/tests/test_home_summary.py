"""The card at the top of Home: the last reviewed match, the day, the goals, the focus."""

from __future__ import annotations

from app.focus_goal import new_focus
from app.home_summary import home_summary, last_match

NOW = 2_000_000_000


def _match(match_id, hours_ago, score, win, improvements=(), strengths=(), analysis=True):
    return {
        "match_id": match_id,
        "hero": "Lion",
        "hero_id": 26,
        "start_time": NOW - hours_ago * 3600,
        "duration": 35 * 60,
        "score": score,
        "win": win,
        "kills": 2,
        "deaths": 7,
        "assists": 15,
        "analysis": {
            "role": "support",
            "improvements": [{"id": i, "section": "survival", "params": {}} for i in improvements],
            "strengths": [
                {"id": s, "section": "vision", "params": {"obs": 12, "sen": 4}} for s in strengths
            ],
            "problems": list(improvements),
            "sections": {"survival": {}, "vision": {}},
        }
        if analysis
        else None,
    }


def test_the_last_reviewed_match_with_its_top_tip_and_strength():
    matches = [
        _match(3, 1, None, None, analysis=False),  # not reviewed yet: skipped
        _match(2, 2, 58, False, improvements=["death_streak"], strengths=["wards_high"]),
        _match(1, 30, 70, True),
    ]
    last = last_match(matches, "ru")
    assert last["match_id"] == 2 and last["hero"] == "Lion" and last["win"] is False
    assert (last["kills"], last["deaths"], last["assists"]) == (2, 7, 15)
    assert last["role"] == "support"
    assert last["tip"]["id"] == "death_streak" and last["tip"]["title"]
    assert last["strength"]["id"] == "wards_high" and last["strength"]["title"]
    assert last_match([_match(1, 1, None, None, analysis=False)], "en") is None


def test_the_summary_carries_the_day_goals_tilt_and_focus():
    focus = new_focus("death_streak", "survival", {})
    focus["since_ts"] = NOW - 100 * 3600
    matches = [
        _match(3, 1, 60, True),
        _match(2, 2, 58, False, improvements=["death_streak"]),
        _match(1, 3, 70, True),
    ]
    today = {"games": 3, "wins": 2, "losses": 1, "avg_score": 63}
    goals = [{"id": "few_deaths", "current": 1, "best": 3, "target": 5, "met": False}]
    summary = home_summary(matches, "en", today=today, goals=goals, tilt=None, focus=focus)
    assert summary["last"]["match_id"] == 3
    assert summary["today"] == today and summary["goals"] == goals and summary["tilt"] is None
    assert [r["met"] for r in summary["focus"]["results"]] == [True, False, True]
    assert (summary["focus"]["met"], summary["focus"]["total"]) == (2, 3)
    assert summary["focus"]["title"]
    no_focus = home_summary(matches, "en", today=None, goals=[], tilt=None, focus=None)
    assert no_focus["focus"] is None
    assert home_summary([], "en", today=None, goals=[], tilt=None, focus=None) is None


def test_summary_endpoint(client):
    assert client.get("/player/summary?lang=ru").json() == {"summary": None}
