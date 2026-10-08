"""Controlled real HTTP/thread interleavings at core MatchMemory boundaries."""

from __future__ import annotations

import sys
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from types import CodeType, FrameType
from typing import Any

import pytest
from fastapi.testclient import TestClient
from test_gsi_snapshot import _packet

from app import main
from app.match_memory import MATCH_MEMORY, MatchMemory


@contextmanager
def _paused_operation(
    pause: CodeType, watch: CodeType
) -> Iterator[tuple[threading.Event, threading.Event, threading.Event]]:
    """Pause a real method, without replacing it or its lock with a fake."""
    entered, watched, release = threading.Event(), threading.Event(), threading.Event()
    original = threading.gettrace()

    def trace(frame: FrameType, event: str, _arg: Any) -> Any:
        if event == "call" and frame.f_code is watch:
            watched.set()
        if event == "call" and frame.f_code is pause:
            sys.settrace(None)
            entered.set()
            assert release.wait(5)
        return None

    threading.settrace(trace)
    try:
        yield entered, watched, release
    finally:
        threading.settrace(original)
        release.set()


def test_http_summary_waits_for_complete_memory_observation(client: TestClient) -> None:
    assert client.post("/gsi", json=_packet()).status_code == 200
    results: dict[str, Any] = {}
    errors: list[Exception] = []
    reader_done = threading.Event()

    def write() -> None:
        try:
            results["writer"] = client.post("/gsi", json=_packet("luna", 70))
        except Exception as error:  # noqa: BLE001 - capture real request failures
            errors.append(error)

    def read() -> None:
        try:
            results["reader"] = client.get("/session/memory")
        except Exception as error:  # noqa: BLE001 - capture real request failures
            errors.append(error)
        finally:
            reader_done.set()

    workers = [threading.Thread(target=write), threading.Thread(target=read)]
    with _paused_operation(
        MatchMemory._annotate_recent_damage.__code__, main.session_memory.__code__
    ) as (entered, watched, release):
        workers[0].start()
        try:
            assert entered.wait(5)  # Hero changed, reset ran, trackers are not complete yet.
            workers[1].start()
            assert watched.wait(5)
            assert not reader_done.wait(0.1)
        finally:
            release.set()
            for worker in workers:
                if worker.ident is not None:
                    worker.join(5)
    assert not any(worker.is_alive() for worker in workers) and not errors
    assert results["writer"].status_code == results["reader"].status_code == 200
    summary = results["reader"].json()
    assert summary["hero"] == "Luna" and summary["last_states_count"] == 1
    assert summary["reset_reason"] == "hero_changed"


def test_http_reset_waits_for_real_demo_memory_writer(client: TestClient) -> None:
    assert client.post("/gsi", json=_packet()).status_code == 200
    results: dict[str, Any] = {}
    errors: list[Exception] = []
    reset_done = threading.Event()

    def demo() -> None:
        try:
            results["demo"] = client.post(
                "/demo/replay-state",
                json={
                    "timestamp_seconds": 600,
                    "state": {
                        "hero": "Luna",
                        "hp_percent": 100,
                        "minute": 10,
                        "game_state": "playing",
                        "extra_context": {"source_type": "replay_gsi_like", "alive": True},
                    },
                },
            )
        except Exception as error:  # noqa: BLE001 - capture real request failures
            errors.append(error)

    def reset() -> None:
        try:
            results["reset"] = client.post("/session/reset")
        except Exception as error:  # noqa: BLE001 - capture real request failures
            errors.append(error)
        finally:
            reset_done.set()

    workers = [threading.Thread(target=demo), threading.Thread(target=reset)]
    with _paused_operation(
        MatchMemory._annotate_recent_damage.__code__, main.reset_session.__code__
    ) as (entered, watched, release):
        workers[0].start()
        try:
            assert entered.wait(5)
            workers[1].start()
            assert watched.wait(5)
            assert not reset_done.wait(0.1)
        finally:
            release.set()
            for worker in workers:
                if worker.ident is not None:
                    worker.join(5)
    assert not any(worker.is_alive() for worker in workers) and not errors
    assert results["demo"].status_code == results["reset"].status_code == 200
    summary = client.get("/session/memory").json()
    assert summary["hero"] is None and summary["last_states_count"] == 0
    assert summary["death_count"] == 0 and summary["reset_reason"] == "manual"
    assert client.get("/state/current").json()["state"] is None


def test_simultaneous_live_and_demo_observers_see_complete_previous_memory(
    client: TestClient,
) -> None:
    assert client.post("/gsi", json=_packet()).status_code == 200
    start = threading.Barrier(3)
    observed: list[tuple[str | None, str, int]] = []
    errors: list[Exception] = []
    responses: list[Any] = []
    original = threading.gettrace()
    real_observe = MatchMemory.observe_state.__wrapped__.__code__

    def trace(frame: FrameType, event: str, _arg: Any) -> Any:
        if event == "call" and frame.f_code is real_observe:
            sys.settrace(None)
            memory = frame.f_locals["self"]
            observed.append((memory.hero, frame.f_locals["state"]["hero"], len(memory.last_states)))
        return None

    def run(demo: bool) -> None:
        try:
            start.wait(5)
            if demo:
                response = client.post(
                    "/demo/replay-state",
                    json={"timestamp_seconds": 600, "state": {"hero": "Phantom Lancer"}},
                )
            else:
                response = client.post("/gsi", json=_packet("luna", 70))
            responses.append(response)
        except Exception as error:  # noqa: BLE001 - capture real request failures
            errors.append(error)

    workers = [threading.Thread(target=run, args=(value,)) for value in (False, True)]
    threading.settrace(trace)
    try:
        for worker in workers:
            worker.start()
        start.wait(5)
        for worker in workers:
            worker.join(5)
    finally:
        threading.settrace(original)
    assert not any(worker.is_alive() for worker in workers) and not errors
    assert len(responses) == 2 and all(response.status_code == 200 for response in responses)
    assert len(observed) == 2 and observed[0][0] == "Juggernaut"
    assert observed[1][0] == observed[0][1] and [row[2] for row in observed] == [1, 1]
    assert client.get("/session/memory").json()["hero"] == observed[-1][1]


def test_exception_releases_owner_and_reentrant_reset_still_works() -> None:
    memory = MatchMemory()
    with pytest.raises(TypeError):
        memory.observe_state({"hero": "Juggernaut", "extra_context": {"match_id": []}})
    completed = threading.Event()
    errors: list[Exception] = []

    def write() -> None:
        try:
            memory.observe_state({"hero": "Juggernaut"})
            memory.observe_state({"hero": "Luna"})  # observe calls reset under the same owner.
            assert memory.summary()["hero"] == "Luna"
            memory.reset()
        except Exception as error:  # noqa: BLE001 - capture real thread failures
            errors.append(error)
        finally:
            completed.set()

    worker = threading.Thread(target=write)
    worker.start()
    worker.join(5)
    assert completed.is_set() and not worker.is_alive() and not errors
    assert memory.summary()["hero"] is None


def test_owned_advice_and_death_views_remain_detached(client: TestClient) -> None:
    alive = _packet()
    alive["hero"].update({"alive": True, "health": 200})
    alive["player"]["deaths"] = 0
    assert client.post("/gsi", json=alive).status_code == 200
    dead = _packet()
    dead["hero"].update({"alive": False, "health": 0, "respawn_seconds": 30})
    dead["player"]["deaths"] = 1
    assert client.post("/gsi", json=dead).status_code == 200
    context = MATCH_MEMORY.overlay_context()
    assert context["recent_death_patterns"]
    expected = list(context["recent_death_patterns"])
    context["recent_death_patterns"].clear()
    assert client.get("/session/memory").json()["recent_death_patterns"] == expected
    assert MATCH_MEMORY.death_review_for_state("foreign", available=False) is None
    assert MATCH_MEMORY.death_review_for_state(context["match_session_id"], available=False)
    MATCH_MEMORY.note_advice("LOW_HP")
    assert client.get("/session/memory").json()["last_advice_type"] == "LOW_HP"
