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
    week = weekly_summary(matches, NOW, "uk")
    assert (week["games"], week["wins"], week["losses"]) == (3, 2, 1)
    assert week["avg_score"] == 65 and week["prev_avg_score"] == 52 and week["score_change"] == 13
    assert week["best"]["match_id"] == 6 and week["best"]["score"] == 72
    assert week["top_problem"]["id"] == "death_streak" and week["top_problem"]["count"] == 2
    assert week["top_problem"]["title"]
    assert "focus" not in week
    # The week's matches for the score chart, oldest first; the week before counted.
    assert [(m["match_id"], m["score"], m["win"]) for m in week["matches"]] == [
        (4, 64, True),
        (5, 58, False),
        (6, 72, True),
    ]
    assert week["prev_games"] == 2
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
    assert client.get("/player/week?lang=uk").json() == {"week": None}
    assert client.get("/player/week?until=1790000000").json() == {"week": None}
    assert client.get("/player/week?until=-5").status_code == 422
    assert client.get("/player/week?until=1790000000&since=1789395200").json() == {"week": None}
    assert client.get("/player/week?since=1789395200").status_code == 422
    assert client.get("/player/week?until=1790000000&since=1790000000").status_code == 422


def test_a_past_week_leaves_out_later_matches_and_names_the_heroes():
    """The Discord post asks for the calendar week that just ended."""
    lina = {**_match(7, 0.2, 80, True), "hero": "Lina", "hero_id": 25}
    matches = [
        lina,
        _match(6, 1.5, 60, True),
        _match(5, 2, 58, False),
        {**_match(4, 3, 64, True), "hero": "Lina", "hero_id": 25},
    ]
    week = weekly_summary(matches, NOW - 86400, "en")
    assert week["games"] == 3, "the match after the week's end is not in it"
    assert week["best"]["match_id"] == 4
    assert week["heroes"] == [
        {"hero": "Juggernaut", "hero_id": 8, "games": 2, "wins": 1},
        {"hero": "Lina", "hero_id": 25, "games": 1, "wins": 1},
    ]


def test_a_past_week_keeps_later_matches_out_of_the_focus_plan():
    focus = new_focus("death_streak", "survival", {})
    focus["since_ts"] = NOW - 3 * WEEK_SECONDS
    matches = [
        _match(4, 0.2, 70, True, ["death_streak"]),  # after the week's end
        _match(3, 2, 60, True),
        _match(2, 3, 62, True),
    ]
    week = weekly_summary(matches, NOW - 86400, "en", focus=focus)
    assert [r["met"] for r in week["focus"]["results"]] == [True, True]


def test_the_period_can_be_a_local_calendar_week():
    """25 hours on a clock-change Sunday: `since` bounds it, not seven fixed days."""
    since = NOW - WEEK_SECONDS - 3600
    matches = [_match(2, 3, 60, True), {**_match(1, 0, 50, False), "start_time": since + 60}]
    assert weekly_summary(matches, NOW, "en", since=since)["games"] == 2
    assert weekly_summary(matches, NOW, "en")["games"] == 1


def test_the_score_note_names_the_side_without_a_score():
    """Before, an unreviewed week against a reviewed one read as "the week before
    has no reviewed matches"."""
    reviewed_before = [_match(2, 9, 60, True)]
    unreviewed = _match(3, 1, None, False)
    assert weekly_summary([unreviewed, *reviewed_before], NOW, "en")["score_note"] == "no_score"
    reviewed = _match(4, 1, 70, True)
    assert weekly_summary([reviewed], NOW, "en")["score_note"] == "no_previous"
    unreviewed_before = _match(5, 9, None, False)
    week = weekly_summary([reviewed, unreviewed_before], NOW, "en")
    assert week["score_note"] == "no_previous_score"
    week = weekly_summary([reviewed, *reviewed_before], NOW, "en")
    assert "score_note" not in week and week["score_change"] == 10
