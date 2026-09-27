"""The home screen's last seven days."""

from __future__ import annotations

from app.focus_goal import new_focus
from app.weekly_summary import WEEK_SECONDS, weekly_summary

NOW = 2_000_000_000


def _match(match_id, days_ago, score, win, problems=()):
    return {
        "match_id": match_id,
        "hero": "Juggernaut",
        "hero_id": 8,
        "start_time": NOW - int(days_ago * 86400),
        "score": score,
        "win": win,
        "analysis": {
            "improvements": [{"id": p, "section": "survival", "params": {}} for p in problems],
            "problems": list(problems),
            "sections": {"survival": {}, "laning": {}},
        },
    }


def test_week_against_the_week_before():
    matches = [  # newest first
        _match(6, 0.5, 72, True, ["death_streak"]),
        _match(5, 2, 58, False, ["death_streak", "draft_better_pick"]),
        _match(4, 3, 64, True, ["lane_deaths"]),
        _match(3, 9, 50, False),
        _match(2, 10, 54, True),
        _match(1, 30, 90, True),
    ]
    week = weekly_summary(matches, NOW, "ru")
    assert (week["games"], week["wins"], week["losses"]) == (3, 2, 1)
    assert week["avg_score"] == 65 and week["prev_avg_score"] == 52 and week["score_change"] == 13
    assert week["best"]["match_id"] == 6 and week["best"]["score"] == 72
    assert week["top_problem"]["id"] == "death_streak" and week["top_problem"]["count"] == 2
    assert week["top_problem"]["title"]
    assert "focus" not in week
    assert weekly_summary(matches[-1:], NOW, "en") is None


def test_the_focus_as_a_three_match_plan():
    focus = new_focus("death_streak", "survival", {})
    focus["since_ts"] = NOW - WEEK_SECONDS
    matches = [
        _match(4, 0.2, 70, True),
        _match(3, 0.5, 60, True, ["death_streak"]),
        _match(2, 1, 62, True),
        _match(1, 2, 61, False),
    ]
    week = weekly_summary(matches, NOW, "en", focus=focus)
    plan = week["focus"]
    assert plan["plan"] == 3 and [r["met"] for r in plan["results"]] == [True, False, True]
    assert plan["met"] == 2 and plan["title"]


def test_week_endpoint(client):
    assert client.get("/player/week?lang=ru").json() == {"week": None}
