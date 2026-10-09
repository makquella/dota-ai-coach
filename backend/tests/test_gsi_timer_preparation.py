"""Cold Roshan/Aegis configuration reads occur before runtime ownership."""

from __future__ import annotations

import sys
import threading
from pathlib import Path
from types import FrameType
from typing import Any

import pytest
from fastapi.testclient import TestClient
from test_gsi_snapshot import _packet

from app import gsi_state, map_hints
from app.gsi_snapshot import GSIRegister
from app.match_memory import MATCH_MEMORY


def _aegis_packet() -> dict[str, Any]:
    packet = _packet()
    packet["map"].update({"clock_time": 1200, "game_time": 1290})
    packet["hero"].update({"aegis": True, "alive": True})
    packet["events"] = [{"event_type": "aegis_picked_up", "game_time": 1290}]
    return packet


def _aegis_state() -> dict[str, Any]:
    return {
        "hero": "Juggernaut",
        "minute": 20,
        "hp_percent": 100,
        "extra_context": {
            "source_type": "live_gsi",
            "clock_time": 1200,
            "game_time": 1290,
            "alive": True,
            "has_aegis": True,
            "gsi_events": [{"type": "aegis_picked_up", "game_time": 1290}],
        },
    }


@pytest.mark.parametrize("source", ["gsi", "demo", "direct"])
def test_cold_timer_file_is_read_outside_both_state_owners(client: TestClient, source: str) -> None:
    reads: list[str] = []
    violations: list[str] = []
    original = threading.gettrace()
    own_trace = sys.gettrace()

    def trace(frame: FrameType, event: str, _arg: Any) -> Any:
        if (
            event == "call"
            and frame.f_code is Path.read_text.__code__
            and frame.f_locals["self"] == map_hints.TIMERS_PATH
        ):
            reads.append(str(frame.f_locals["self"]))
            caller = frame.f_back
            while caller is not None:
                if caller.f_code is GSIRegister.update.__code__ or (
                    caller.f_code.co_name == "guarded"
                    and caller.f_locals.get("self") is MATCH_MEMORY
                ):
                    violations.append(caller.f_code.co_name)
                caller = caller.f_back
        return None

    map_hints.timers.cache_clear()
    threading.settrace(trace)
    sys.settrace(trace)
    try:
        if source == "gsi":
            assert client.post("/gsi", json=_aegis_packet()).status_code == 200
        elif source == "demo":
            assert (
                client.post(
                    "/demo/replay-state",
                    json={"timestamp_seconds": 1200, "state": _aegis_state()},
                ).status_code
                == 200
            )
        else:
            MATCH_MEMORY.observe_state(_aegis_state())
        assert MATCH_MEMORY.roshan.aegis_at == 1200
        assert len(reads) == 1 and violations == []
    finally:
        threading.settrace(original)
        sys.settrace(own_trace)
        map_hints.timers.cache_clear()


def test_blocked_cold_timer_read_does_not_block_reset_on_one_asgi_loop(
    client: TestClient,
) -> None:
    _reset_during_cold_read(client)


def _reset_during_cold_read(client: TestClient) -> None:
    entered, release, reset_done = threading.Event(), threading.Event(), threading.Event()
    responses: dict[str, Any] = {}
    errors: list[Exception] = []
    original = threading.gettrace()

    def trace(frame: FrameType, event: str, _arg: Any) -> Any:
        if (
            event == "call"
            and frame.f_code is Path.read_text.__code__
            and frame.f_locals["self"] == map_hints.TIMERS_PATH
        ):
            sys.settrace(None)
            entered.set()
            assert release.wait(5)
        return None

    def write() -> None:
        try:
            responses["writer"] = client.post("/gsi", json=_aegis_packet())
        except Exception as error:  # noqa: BLE001 - capture real request failures
            errors.append(error)

    def reset() -> None:
        try:
            responses["reset"] = client.post("/session/reset")
        except Exception as error:  # noqa: BLE001 - capture real request failures
            errors.append(error)
        finally:
            reset_done.set()

    workers = [threading.Thread(target=write), threading.Thread(target=reset)]
    map_hints.timers.cache_clear()
    threading.settrace(trace)
    # Startup now warms KB on a worker; trace before entering lifespan.
    with client:
        try:
            workers[0].start()
            assert entered.wait(5)
            workers[1].start()
            assert reset_done.wait(2) and responses["reset"].status_code == 200
            assert client.get("/session/memory").json()["hero"] is None
            assert client.get("/state/current").json()["state"] is None
        finally:
            threading.settrace(original)
            release.set()
            for worker in workers:
                if worker.ident is not None:
                    worker.join(5)
            map_hints.timers.cache_clear()
    assert not any(worker.is_alive() for worker in workers) and not errors
    assert responses["writer"].status_code == 200
    assert MATCH_MEMORY.roshan.aegis_at == 1200


def test_direct_register_enrichment_also_prepares_timer_settings_before_ownership() -> None:
    map_hints.timers.cache_clear()
    entered_under_writer: list[bool] = []
    original = sys.gettrace()

    def trace(frame: FrameType, event: str, _arg: Any) -> Any:
        if (
            event == "call"
            and frame.f_code is Path.read_text.__code__
            and frame.f_locals["self"] == map_hints.TIMERS_PATH
        ):
            caller = frame.f_back
            while caller is not None:
                if caller.f_code is GSIRegister.update.__code__:
                    entered_under_writer.append(True)
                caller = caller.f_back
        return None

    sys.settrace(trace)
    try:
        response = gsi_state.update_latest_gsi(_aegis_packet(), enrich=MATCH_MEMORY.observe_state)
        assert response["state"]["hero"] == "Juggernaut"
        assert MATCH_MEMORY.roshan.aegis_at == 1200
        assert entered_under_writer == [] and map_hints.timers.cache_info().misses == 1
    finally:
        sys.settrace(original)
        map_hints.timers.cache_clear()
