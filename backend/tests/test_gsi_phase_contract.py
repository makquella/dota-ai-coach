"""Nightly seed 12: malformed phase containers must not break a dead hero packet."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient
from test_gsi_snapshot import _packet

from app.gsi_state import normalize_gsi_payload


@pytest.mark.parametrize("phase", [{}, {"pressure": True}, [], ["strategy"], True, 123])
def test_invalid_dead_hero_phase_remains_unknown_through_actual_launcher_requests(
    client: TestClient,
    phase: Any,
) -> None:
    packet = _packet()
    packet["map"]["game_state"] = phase
    packet["hero"].update({"alive": False, "health": 0, "respawn_seconds": 30})
    response = client.post("/gsi", json=packet)
    assert response.status_code == 200
    state = response.json()["state"]
    assert state["game_state"] == "gsi_update"
    assert state["extra_context"]["alive"] is False
    for path in (
        "/overlay/recommendation",
        "/overlay/recommendation?lang=uk",
        "/gsi/status",
        "/player",
    ):
        result = client.get(path)
        assert result.status_code == 200, (path, result.text)


def test_nontext_event_values_do_not_invent_pressure_and_valid_phase_fallback_is_preserved() -> (
    None
):
    packet = _packet()
    packet.update({"game_state": {"pressure": True}, "event": ["fight"]})
    packet["map"]["name"] = 123
    state = normalize_gsi_payload(packet)
    assert state["game_state"] == "DOTA_GAMERULES_STATE_GAME_IN_PROGRESS"
    packet["map"]["game_state"] = None
    assert normalize_gsi_payload(packet)["game_state"] == "gsi_update"


def test_valid_pre_spawn_phase_still_corrects_false_dead_hero_signal(client: TestClient) -> None:
    packet = _packet()
    packet["map"]["game_state"] = "DOTA_GAMERULES_STATE_STRATEGY_TIME"
    packet["hero"].update({"alive": False, "health": 0})
    response = client.post("/gsi", json=packet)
    assert response.status_code == 200
    assert response.json()["state"]["extra_context"]["alive"] is True
    assert client.get("/overlay/recommendation").json()["decision_point"] not in {
        "DEATH",
        "DEATH_LOW_RESOURCE",
    }
