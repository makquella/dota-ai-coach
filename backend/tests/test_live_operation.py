"""F10: a GSI packet, an overlay poll, a demo state and a session reset each
run whole (app/live_operation.py): a poll or a reset waits for a packet whose
MatchMemory enrichment is still running, and disk work (the advice log) runs
outside the operation. Real app, HTTP and controlled threads."""

from __future__ import annotations

import sys
import threading
from types import FrameType
from typing import Any

from fastapi.testclient import TestClient
from match_fixtures import gsi_match_stream

from app import live_operation as live_operation_module
from app import logger as logger_module
from app.match_memory import MatchMemory


def _paused_in(code, entered: threading.Event, release: threading.Event):
    def trace(frame: FrameType, event: str, _arg: Any) -> Any:
        if event == "call" and frame.f_code is code:
            sys.settrace(None)
            entered.set()
            assert release.wait(10)
        return None

    return trace


def _stream() -> list[dict[str, Any]]:
    return gsi_match_stream(minutes=6, step_seconds=30, death_minutes=(4,))


def _in_background(fn) -> tuple[threading.Thread, list[Any], threading.Event]:
    results: list[Any] = []
    done = threading.Event()

    def run() -> None:
        try:
            results.append(fn())
        finally:
            done.set()

    thread = threading.Thread(target=run)
    thread.start()
    return thread, results, done


def test_an_overlay_poll_waits_for_the_packet_being_enriched(client: TestClient) -> None:
    stream = _stream()
    for payload in stream[:-1]:
        client.post("/gsi", json=payload)
    entered, release = threading.Event(), threading.Event()
    original = threading.gettrace()
    threading.settrace(
        _paused_in(
            MatchMemory.observe_state.__wrapped__.__code__
            if hasattr(MatchMemory.observe_state, "__wrapped__")
            else MatchMemory.observe_state.__code__,
            entered,
            release,
        )
    )
    writer, _, written = _in_background(lambda: client.post("/gsi", json=stream[-1]))
    try:
        assert entered.wait(10)
        threading.settrace(original)
        reader, polls, polled = _in_background(lambda: client.get("/overlay/recommendation"))
        # The poll cannot pair the old snapshot with half-updated match memory.
        assert not polled.wait(0.5)
    finally:
        threading.settrace(original)
        release.set()
    writer.join(10)
    reader.join(10)
    assert written.is_set() and polled.is_set()
    assert polls[0].status_code == 200
    clock = stream[-1]["map"]["clock_time"]
    status = client.get("/gsi/status").json()
    assert status["clock_time"] == clock


def test_a_session_reset_waits_for_the_packet_being_enriched(client: TestClient) -> None:
    stream = _stream()
    client.post("/gsi", json=stream[0])
    entered, release = threading.Event(), threading.Event()
    original = threading.gettrace()
    code = (
        MatchMemory.observe_state.__wrapped__.__code__
        if hasattr(MatchMemory.observe_state, "__wrapped__")
        else MatchMemory.observe_state.__code__
    )
    threading.settrace(_paused_in(code, entered, release))
    writer, _, _ = _in_background(lambda: client.post("/gsi", json=stream[1]))
    try:
        assert entered.wait(10)
        threading.settrace(original)
        resetter, resets, reset_done = _in_background(lambda: client.post("/session/reset"))
        assert not reset_done.wait(0.5), "the reset landed inside a packet"
    finally:
        threading.settrace(original)
        release.set()
    writer.join(10)
    resetter.join(10)
    assert resets[0].status_code == 200
    # The reset ran after the whole packet: nothing of it is left.
    assert client.get("/gsi/status").json()["gsi_connected"] is False
    assert client.get("/session/memory").json().get("death_count", 0) == 0


def test_the_advice_log_is_written_outside_the_live_operation(
    client: TestClient, monkeypatch
) -> None:
    held: list[bool] = []
    real_log = logger_module.log_recommendation

    def probe(**kwargs):
        free = threading.Event()

        def try_lock() -> None:
            if live_operation_module._LOCK.acquire(timeout=0.5):
                live_operation_module._LOCK.release()
                free.set()

        other = threading.Thread(target=try_lock)
        other.start()
        other.join(2)
        held.append(not free.is_set())
        return real_log(**kwargs)

    import app.main as main_module

    monkeypatch.setattr(main_module, "log_recommendation", probe)
    for payload in gsi_match_stream(minutes=8, step_seconds=10, death_minutes=(3, 6)):
        client.post("/gsi", json=payload)
        client.get("/overlay/recommendation")
    assert held, "no advice was logged"
    assert not any(held)
