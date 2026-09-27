"""The player's advice frequency scales coaching pauses, never urgent advice."""

from __future__ import annotations

import json

import pytest

from app.advice_scheduler import ADVICE_SCHEDULER
from app.scheduler.frequency import heartbeat_enabled, normalize_frequency, scaled_seconds

REPLAY = "data/match_simulations/replay_gsi_like_match_8843382732_pl_20_30.jsonl"


def test_values_and_scaling():
    assert normalize_frequency("ACTIVE") == "active"
    assert normalize_frequency("loud") == "normal"
    assert scaled_seconds(45, "calm") == 90
    assert scaled_seconds(45, "active") == 27
    assert heartbeat_enabled("normal") and not heartbeat_enabled("calm")


@pytest.mark.parametrize("frequency", ["calm", "active"])
def test_safety_cooldowns_do_not_scale(frequency):
    ADVICE_SCHEDULER.set_frequency(frequency)
    regular = ADVICE_SCHEDULER.regular_cooldown_seconds
    for decision in ("LOW_HP_WARNING", "RECENT_DAMAGE_WARNING", "ABILITY_SAFETY_COOLDOWN"):
        assert ADVICE_SCHEDULER._cooldown_for_type_locked(decision) == regular
    assert ADVICE_SCHEDULER._cooldown_for_type_locked("LOW_HP") == (
        ADVICE_SCHEDULER.urgent_cooldown_seconds
    )
    assert ADVICE_SCHEDULER._cooldown_for_type_locked("SAFE_FARMING") == scaled_seconds(
        regular, frequency
    )


def test_api_round_trip(client):
    assert client.get("/settings/advice").json()["frequency"] == "normal"
    answer = client.post("/settings/advice", json={"frequency": "calm"}).json()
    assert answer["frequency"] == "calm" and answer["options"] == ["calm", "normal", "active"]
    # Role and map hints are separate fields of the same settings.
    assert answer["role"] == "auto" and answer["map_hints"] is True
    answer = client.post("/settings/advice", json={"role": "support", "map_hints": False}).json()
    assert (answer["frequency"], answer["role"], answer["map_hints"]) == ("calm", "support", False)
    assert client.post("/settings/advice", json={"role": "jungle"}).json()["role"] == "auto"
    assert client.post("/settings/advice", json={"frequency": "?"}).json()["frequency"] == "normal"
    # A new match keeps the preference.
    ADVICE_SCHEDULER.set_frequency("active")
    ADVICE_SCHEDULER.reset()
    assert ADVICE_SCHEDULER.frequency == "active"


def _run(client, repo_root, frequency: str) -> tuple[int, int]:
    ADVICE_SCHEDULER.reset()
    ADVICE_SCHEDULER.set_frequency(frequency)
    shown = urgent = 0
    for line in (repo_root / REPLAY).read_text(encoding="utf-8").splitlines():
        item = json.loads(line)
        overlay = client.post(
            "/demo/replay-state",
            json={"timestamp_seconds": item["timestamp_seconds"], "state": item["state"]},
        ).json()["overlay"]
        if overlay.get("new_advice") and overlay.get("recommendation"):
            shown += 1
            urgent += overlay.get("advice_mode") == "urgent"
    return shown, urgent


@pytest.mark.parametrize("frequency", ["calm", "active"])
def test_frequency_changes_coaching_only(client, repo_root, frequency):
    normal, normal_urgent = _run(client, repo_root, "normal")
    shown, urgent = _run(client, repo_root, frequency)
    assert urgent == normal_urgent
    assert (shown < normal) if frequency == "calm" else (shown > normal)
