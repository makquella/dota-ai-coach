"""A kill somewhere on the map (the team score in live GSI) is not a fight near the player."""

from __future__ import annotations

import copy

from match_fixtures import gsi_match_stream

from app.decision_points import detect_decision_point
from app.gsi_state import get_current_state


def _state(**extra):
    return {
        "hero": "Juggernaut",
        "minute": 6,
        "level": 6,
        "gold": 400,
        "hp_percent": 90,
        "game_state": "laning",
        "extra_context": {"alive": True, "mana_percent": 80, **extra},
    }


def test_score_change_alone_is_not_a_bad_fight():
    assert detect_decision_point(_state(score_changed=True)) != "BAD_FIGHT_RISK"


def test_score_change_next_to_a_fight_still_is():
    state = _state(score_changed=True)
    state["near_teamfight"] = True
    assert detect_decision_point(state) == "BAD_FIGHT_RISK"


def test_first_blood_elsewhere_gives_no_fight_warning(client):
    stream = gsi_match_stream(minutes=2, death_minutes=())
    for payload in stream:
        payload = copy.deepcopy(payload)
        client.post("/gsi", json=payload)
        state = get_current_state()["state"]
        assert detect_decision_point(state) != "BAD_FIGHT_RISK", payload["map"]["clock_time"]


def test_counters_that_go_down_are_not_events(client):
    first = copy.deepcopy(gsi_match_stream(minutes=1, death_minutes=())[-2])
    first["player"]["deaths"] = 3
    first["map"]["radiant_score"] = 12
    client.post("/gsi", json=first)
    second = copy.deepcopy(first)
    second["map"]["clock_time"] += 1
    second["player"]["deaths"] = 0  # reconnect / replay seek
    second["map"]["radiant_score"] = 4
    client.post("/gsi", json=second)
    extra = get_current_state()["state"]["extra_context"]
    assert extra["death_count_changed"] is False and extra["score_changed"] is False
    third = copy.deepcopy(second)
    third["map"]["clock_time"] += 1
    third["player"]["deaths"] = 1
    client.post("/gsi", json=third)
    assert get_current_state()["state"]["extra_context"]["death_count_changed"] is True
