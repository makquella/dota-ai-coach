"""Real history ownership, bounded message catalogs and unchanged HTTP polls."""

from __future__ import annotations

import copy
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from types import FrameType
from typing import Any

from fastapi.testclient import TestClient
from test_gsi_snapshot import _packet

from app import advice_i18n
from app.coach_summary import MAX_HISTORY, CoachSessionHistory


def _response(count: int = 1) -> dict[str, Any]:
    return {
        "status": "advice",
        "advice_count": count,
        "decision_point": "LOW_HP",
        "recommendation": {
            "action": "Keep farming safely.",
            "reason": "HP is stable and no pressure signal is active.",
        },
        "hero": "Juggernaut",
        "source": "fallback",
        "minute": 10,
    }


def test_concurrent_duplicate_history_has_one_private_record_and_stable_identity() -> None:
    history = CoachSessionHistory()
    response = _response()
    state = {"extra_context": {"missing_signals": ["enemy_positions"]}}
    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(lambda _i: history.record_overlay_advice(response, state), range(24)))
    stored = history.records()
    assert len(stored) == 1
    original_id = stored[0]["id"]
    response["recommendation"]["action"] = "changed"
    state["extra_context"]["missing_signals"].append("changed")
    stored[0]["action_message"]["id"] = "changed"
    assert history.records()[0]["action"] == "Keep farming safely."
    assert history.records()[0]["missing_signals"] == ["enemy_positions"]
    assert history.records()[0]["id"] == original_id
    history.reset()
    history.record_overlay_advice(_response())
    assert history.records()[0]["id"] != original_id


def test_recent_selection_copies_only_requested_records_and_retains_history_bound() -> None:
    history = CoachSessionHistory()
    for count in range(MAX_HISTORY + 10):
        history.record_overlay_advice(_response(count))
    assert len(history.records()) == MAX_HISTORY
    copied = []
    previous = sys.gettrace()

    def trace(frame: FrameType, event: str, _arg: Any) -> Any:
        if event == "call" and frame.f_code is copy.deepcopy.__code__:
            value = frame.f_locals.get("x")
            if isinstance(value, dict) and "timestamp" in value and "id" in value:
                copied.append(value["id"])
        return None

    sys.settrace(trace)
    try:
        selected = history.records(2)
    finally:
        sys.settrace(previous)
    assert len(selected) == 2 and copied == [r["id"] for r in selected]
    assert history.records(0) == [] and history.records(-1) == []
    selected[0]["action"] = "changed"
    assert history.records(1)[0]["action"] == "Keep farming safely."


def test_reset_rejects_actual_prepared_append_from_previous_generation() -> None:
    history = CoachSessionHistory()
    entered, release = threading.Event(), threading.Event()
    previous = threading.gettrace()
    errors = []

    def trace(frame: FrameType, event: str, _arg: Any) -> Any:
        if event == "call" and frame.f_code is CoachSessionHistory._append_prepared.__code__:
            if frame.f_locals["self"] is history:
                sys.settrace(None)
                entered.set()
                assert release.wait(5)
        return None

    def append() -> None:
        try:
            history.record_overlay_advice(_response())
        except Exception as error:  # noqa: BLE001 - inspect real thread failures
            errors.append(error)

    threading.settrace(trace)
    worker = threading.Thread(target=append)
    worker.start()
    try:
        assert entered.wait(5)
        history.reset()
        history.record_overlay_advice(_response(2))
        new_id = history.records()[0]["id"]
    finally:
        release.set()
        worker.join(5)
        threading.settrace(previous)
    assert not worker.is_alive() and not errors
    assert [r["id"] for r in history.records()] == [new_id]


def test_real_recent_http_reuses_ids_params_and_does_not_rescan_unchanged_text(
    client: TestClient,
) -> None:
    packet = _packet()
    packet["hero"]["health"] = 100
    assert client.post("/gsi", json=packet).status_code == 200
    shown = client.get("/overlay/recommendation").json()
    assert shown["recommendation"]["action_message"]["id"].startswith("live.")
    english = client.get("/advice/recent").json()["items"]
    first = client.get("/advice/recent?lang=uk").json()["items"]
    assert first[0]["id"] == english[0]["id"]
    assert first[0]["action"] == advice_i18n.translate_uk(english[0]["action"])
    calls = []
    previous = threading.gettrace()
    watched = {
        advice_i18n.translate_uk.__code__,
        advice_i18n._message_for_text.__wrapped__.__code__,
        advice_i18n._render_message.__wrapped__.__code__,
    }

    def trace(frame: FrameType, event: str, _arg: Any) -> Any:
        if event == "call" and frame.f_code in watched:
            calls.append(frame.f_code.co_name)
        return None

    threading.settrace(trace)
    try:
        second = client.get("/advice/recent?lang=uk").json()["items"]
        again = client.get("/advice/recent").json()["items"]
    finally:
        threading.settrace(previous)
    assert second == first and again == english and calls == []
    assert client.post("/session/reset").status_code == 200
    assert client.get("/advice/recent?lang=uk").json()["items"] == []


def test_message_ids_params_preserve_legacy_translation_semantics_and_fallbacks() -> None:
    cases = list(advice_i18n._UK_EXACT) + [
        "Avoid risky trades until Blade Fury is ready.",
        "After respawn, change your route: 3 deaths in the last 5 minutes.",
        "Consider leave the wave now and reset HP before rejoining.",
        "Keep farming safely. Focus on safe last hits.",
        "Keep farming safely. Something the table does not know.",
        "Something the table does not know.",
        "Your farm pace is behind for this minute, but HP is stable, so the fastest...",
    ]
    for canonical in cases:
        entry = advice_i18n.advice_messages({"action": canonical})
        localized = advice_i18n.localize_advice_items([entry], "uk")[0]
        assert localized["action"] == (advice_i18n.translate_uk(canonical) or canonical), canonical
        assert entry["action"] == canonical
        assert advice_i18n.localize_advice_items([entry], "en")[0]["action"] == canonical
    first = advice_i18n.advice_messages({"action": "Avoid risky trades until Blade Fury is ready."})
    other = advice_i18n.advice_messages({"action": "Avoid risky trades until Blink is ready."})
    assert first["action_message"]["id"] == other["action_message"]["id"]
    assert first["action_message"]["params"] != other["action_message"]["params"]
    first["action_message"]["params"] = {}  # Invalid descriptor keeps legacy fallback.
    assert advice_i18n.localize_advice_items([first], "uk")[0][
        "action"
    ] == advice_i18n.translate_uk(first["action"])


def test_message_and_render_caches_are_bounded() -> None:
    for count in range(600):
        entry = advice_i18n.advice_messages(
            {"action": f"Avoid risky trades until Skill {count} is ready."}
        )
        localized = advice_i18n.localize_advice_items([entry], "uk")[0]
        assert str(count) in localized["action"]
    assert advice_i18n._message_for_text.cache_info().currsize <= 512
    assert advice_i18n._render_message.cache_info().currsize <= 512
