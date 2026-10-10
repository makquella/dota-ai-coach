from __future__ import annotations

import pytest

from app import main

COMMON = {
    "recommendation": None,
    "llm_used": False,
    "source": "none",
    "next_allowed_advice_in_seconds": 0,
    "advice_mode": "status",
    "active_advice_until": None,
    "last_visible_advice": None,
    "is_pinned": False,
}


def test_status_answer_keeps_shared_fields_and_its_own_reason() -> None:
    answer = main._overlay_status(
        "stale_gsi",
        {},
        last_updated="2026-01-01T00:00:00+00:00",
        suppressed_reason="stale_gsi",
        message="Waiting for live GSI...",
        gsi_stale=True,
    )

    assert answer.items() >= COMMON.items()
    assert answer["status"] == "stale_gsi" and answer["decision_point"] == "NO_ADVICE"
    assert answer["suppressed_reason"] == "stale_gsi" and answer["gsi_stale"] is True
    assert answer["message"] == "Waiting for live GSI..."
    assert answer["last_updated"] == "2026-01-01T00:00:00+00:00"
    assert answer["advice_count"] == main.ADVICE_SCHEDULER.stats()["advice_count"]
    assert answer.items() >= main._overlay_live_context({}).items()


def test_status_without_message_has_no_message_key() -> None:
    answer = main._overlay_status(
        "monitoring",
        {},
        last_updated=None,
        suppressed_reason=None,
        decision_point="SOFT_STATUS",
    )

    assert "message" not in answer
    assert answer["decision_point"] == "SOFT_STATUS" and answer["suppressed_reason"] is None


def test_invalid_state_answer_carries_validation_detail(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(main, "detect_decision_point", lambda _state: "LOW_HP")
    state = {"hero": "Juggernaut", "minute": 500, "level": 6, "gold": 100, "items": []}

    answer = main._overlay_response_for_state(state, timestamp="t")

    assert answer["status"] == "invalid_state" and answer["decision_point"] == "LOW_HP"
    assert answer.items() >= COMMON.items()
    assert answer["suppressed_reason"] is None and answer["last_updated"] == "t"
    assert isinstance(answer["detail"], list) and answer["detail"]


def test_waiting_for_gsi_poll_answer(client) -> None:
    answer = client.get("/overlay/recommendation").json()

    assert answer["status"] == "waiting_for_gsi" and answer["last_updated"] is None
    assert answer["suppressed_reason"] == "no_advice"
    assert answer.items() >= COMMON.items()
