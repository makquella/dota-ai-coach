"""Streak goals, the tilt warning (app/player_goals.py) and the hero pool advice."""

from __future__ import annotations

from app.career_analysis import hero_pool
from app.player_goals import goal_streaks, tilt

NOW = 1_800_000_000
HOUR = 3600


def _row(start, *, win=True, deaths=3, score=None, duration=40 * 60):
    return {"start_time": start, "duration": duration, "win": win, "deaths": deaths, "score": score}


def _goal(goals, goal_id):
    return next(g for g in goals if g["id"] == goal_id)


def test_goal_runs_count_from_the_newest_match():
    rows = [
        _row(NOW, deaths=4, score=70),
        _row(NOW - HOUR, deaths=2, score=None),  # not reviewed yet: skipped for the score
        _row(NOW - 2 * HOUR, deaths=5, score=65),
        _row(NOW - 3 * HOUR, deaths=9, score=50),
        _row(NOW - 4 * HOUR, deaths=1, score=80),
        _row(NOW - 5 * HOUR, deaths=0, score=81),
        _row(NOW - 6 * HOUR, deaths=3, score=90),
        _row(NOW - 7 * HOUR, deaths=4, score=61),
    ]
    goals = goal_streaks(rows)
    deaths = _goal(goals, "few_deaths")
    assert deaths == {"id": "few_deaths", "current": 3, "best": 4, "target": 5, "met": False}
    score = _goal(goals, "good_score")
    assert score == {"id": "good_score", "current": 2, "best": 4, "target": 3, "met": False}
    rows[3]["score"] = 60
    assert _goal(goal_streaks(rows), "good_score")["met"] is True
    assert goal_streaks([]) == []


def test_three_losses_in_a_row_this_session_is_tilt():
    rows = [
        _row(NOW - HOUR, win=False),
        _row(NOW - 2 * HOUR, win=False),
        _row(NOW - 3 * HOUR, win=False),
        _row(NOW - 4 * HOUR, win=True),
    ]
    assert tilt(rows, NOW) == {"reason": "losses", "losses": 3, "games": 4}
    # A win at the end breaks it; so does a long break since the last match.
    assert tilt([_row(NOW - HOUR, win=True), *rows], NOW) is None
    assert tilt(rows, NOW + 3 * HOUR) is None
    # Losses of another day (a gap between starts) do not chain into the session.
    split = [rows[0], rows[1], _row(NOW - 30 * HOUR, win=False)]
    assert tilt(split, NOW) is None


def test_two_scores_far_below_the_usual_is_tilt():
    earlier = [_row(NOW - (10 + i) * HOUR, win=i % 2 == 0, score=62) for i in range(6)]
    rows = [_row(NOW - HOUR, win=False, score=35), _row(NOW - 2 * HOUR, score=40), *earlier]
    assert tilt(rows, NOW) == {"reason": "score_drop", "scores": [35, 40], "usual": 62, "games": 2}
    # One bad game is not tilt; nor is a drop without enough earlier scores.
    rows[1]["score"] = 58
    assert tilt(rows, NOW) is None
    rows[1]["score"] = 40
    assert tilt(rows[:5], NOW) is None


def _hero(name, matches, wins, bracket=None):
    return {
        "hero": name,
        "hero_id": 1,
        "matches": matches,
        "wins": wins,
        "winrate": round(100 * wins / matches),
        "bracket_winrate": bracket,
    }


def test_hero_pool_play_more_and_park():
    pool = hero_pool(
        [
            _hero("Juggernaut", 8, 6, bracket=51),  # 75 %: play more
            _hero("Axe", 6, 4, bracket=64),  # 67 %, but the rank plays it at 64 %: not enough
            _hero("Lina", 5, 1, bracket=48),  # 20 %: park
            _hero("Sniper", 3, 0),  # too few games
            _hero("Zeus", 6, 2),  # 33 %, no rank data: park
        ]
    )
    assert [e["hero"] for e in pool["play_more"]] == ["Juggernaut"]
    assert [e["hero"] for e in pool["park"]] == ["Lina", "Zeus"]
    assert hero_pool([_hero("Axe", 6, 3)]) is None


def test_the_status_carries_goals_and_tilt(client):
    from app.player_api import PLAYER_SERVICE

    PLAYER_SERVICE.store.upsert_player(1234, source="manual")
    PLAYER_SERVICE.store.set_primary(1234, source="manual")
    body = client.get("/player").json()
    assert body["goals"] == [] and body["tilt"] is None
