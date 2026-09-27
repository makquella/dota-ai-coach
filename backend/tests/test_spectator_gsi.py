"""Watching a replay or someone's live game in the Dota client must not end up
in the linked player's history."""

from __future__ import annotations

import copy

from match_fixtures import MATCH_ID, ME, gsi_match_stream

from app.match_tracker import MatchTracker, is_spectator_payload
from app.player_api import PLAYER_SERVICE

SPECTATED_MATCH = 8123456789


def _spectator_stream(minutes=12):
    """GSI of a spectated game: every player and hero per team, no local player."""
    players = {
        "team2": {f"player{i}": {"steamid": str(76561197960265728 + 1000 + i)} for i in range(5)},
        "team3": {
            f"player{i}": {"steamid": str(76561197960265728 + 1000 + i)} for i in range(5, 10)
        },
    }
    heroes = {
        "team2": {f"player{i}": {"name": "npc_dota_hero_juggernaut"} for i in range(5)},
        "team3": {f"player{i}": {"name": "npc_dota_hero_axe"} for i in range(5, 10)},
    }
    return [
        {
            "provider": {"name": "Dota 2", "appid": 570},
            "map": {
                "matchid": str(SPECTATED_MATCH),
                "clock_time": t,
                "game_state": "DOTA_GAMERULES_STATE_GAME_IN_PROGRESS",
            },
            "player": copy.deepcopy(players),
            "hero": copy.deepcopy(heroes),
        }
        for t in range(0, minutes * 60 + 1, 15)
    ]


def test_spectator_payloads_are_recognised():
    assert is_spectator_payload(_spectator_stream(1)[0])
    assert not is_spectator_payload(gsi_match_stream(minutes=1)[0])
    assert not is_spectator_payload({"player": "odd", "hero": None})


def test_tracker_ignores_a_spectated_game(tmp_path):
    finished = []
    tracker = MatchTracker(tmp_path / "live.json", on_finished=finished.append)
    for payload in _spectator_stream():
        tracker.observe(payload)
    assert tracker.current() is None
    tracker._clock = lambda: float("inf")
    tracker.check_stale()
    assert finished == []


def test_a_timeline_without_a_hero_is_not_reviewed(tmp_path):
    finished = []
    tracker = MatchTracker(tmp_path / "live.json", on_finished=finished.append)
    for payload in gsi_match_stream(minutes=8):
        payload = copy.deepcopy(payload)
        payload.pop("hero")
        tracker.observe(payload)
    assert finished == []


def test_watching_a_replay_after_a_match_keeps_history_clean(client, tmp_path):
    PLAYER_SERVICE.configure(tmp_path / "svc", client=None, auto_start=False)
    for payload in gsi_match_stream(minutes=10)[:-1]:
        client.post("/gsi", json=payload)
    # Straight into a replay: ignored, so the own match ends as usual (here
    # when GSI goes quiet) and the replay is never recorded.
    for payload in _spectator_stream():
        client.post("/gsi", json=payload)
    PLAYER_SERVICE.tracker._clock = lambda: float("inf")
    PLAYER_SERVICE.check_stale()
    matches = client.get("/player/matches").json()["items"]
    assert [m["match_id"] for m in matches] == [MATCH_ID]
    assert client.get("/player").json()["account_id"] == ME
    overlay = client.get("/overlay/recommendation").json()
    assert overlay["recommendation"] is None and "game_plan" not in overlay
