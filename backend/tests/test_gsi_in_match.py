from __future__ import annotations

import json


def _status(client) -> dict:
    response = client.get("/gsi/status")
    assert response.status_code == 200
    return response.json()


def test_in_match_is_false_before_any_gsi(client):
    assert _status(client)["in_match"] is False


def test_in_match_is_true_for_fresh_match_payload(client, repo_root):
    sample = repo_root / "data" / "gsi_samples" / "calm_farming_antimage.json"
    client.post("/gsi", json=json.loads(sample.read_text(encoding="utf-8")))

    status = _status(client)

    assert status["gsi_connected"] is True
    assert status["in_match"] is True


def test_main_menu_heartbeat_is_fresh_but_not_in_match(client):
    client.post("/gsi", json={"provider": {"name": "Dota 2", "appid": 570}})

    status = _status(client)

    assert status["gsi_connected"] is True
    assert status["in_match"] is False


def test_hero_selection_is_not_in_match(client):
    client.post(
        "/gsi",
        json={
            "map": {"game_state": "DOTA_GAMERULES_STATE_HERO_SELECTION"},
            "hero": {"name": "npc_dota_hero_juggernaut"},
        },
    )

    assert _status(client)["in_match"] is False


def test_post_game_is_not_in_match(client):
    client.post(
        "/gsi",
        json={
            "map": {"game_state": "DOTA_GAMERULES_STATE_POST_GAME"},
            "hero": {"name": "npc_dota_hero_juggernaut"},
        },
    )

    assert _status(client)["in_match"] is False


def test_stale_match_payload_is_not_in_match(client, repo_root, monkeypatch):
    from app import main

    sample = repo_root / "data" / "gsi_samples" / "calm_farming_antimage.json"
    client.post("/gsi", json=json.loads(sample.read_text(encoding="utf-8")))
    monkeypatch.setattr(main, "_seconds_since_timestamp", lambda _timestamp: 60.0)

    status = _status(client)

    assert status["gsi_connected"] is False
    assert status["in_match"] is False
