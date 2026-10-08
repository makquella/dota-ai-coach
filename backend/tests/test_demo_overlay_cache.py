"""Detached demo publication, reset invalidation and real concurrent requests."""

from __future__ import annotations

import copy
import sys
import threading
from types import FrameType
from typing import Any

import pytest
from fastapi.testclient import TestClient
from test_match_memory_ownership import _paused_operation

from app import main
from app.demo_overlay_cache import DemoOverlayCache


def _demo(hero: str = "Juggernaut", clock: int = 600) -> dict[str, Any]:
    return {
        "timestamp_seconds": clock,
        "state": {
            "hero": hero,
            "hp_percent": 100,
            "minute": clock // 60,
            "game_state": "playing",
            "extra_context": {"source_type": "replay_gsi_like", "alive": True},
        },
    }


@pytest.mark.parametrize("operation", ["reset", "newer_demo"])
def test_delayed_real_demo_cannot_replace_reset_or_newer_response(
    client: TestClient, operation: str
) -> None:
    responses: list[Any] = []
    errors: list[Exception] = []

    def old_demo() -> None:
        try:
            responses.append(client.post("/demo/replay-state", json=_demo()))
        except Exception as error:  # noqa: BLE001 - inspect real request failure
            errors.append(error)

    worker = threading.Thread(target=old_demo)
    with _paused_operation(
        main._set_demo_overlay_response.__code__, main.reset_session.__code__
    ) as (entered, _watched, release):
        worker.start()
        try:
            assert entered.wait(5)  # response/history computed, publication not started
            if operation == "reset":
                assert client.post("/session/reset").status_code == 200
                assert main._get_demo_overlay_response() is None
            else:
                # Avoid tracing this independent portal, which intentionally
                # calls the same publisher: only the old request stays paused.
                previous = threading.gettrace()
                threading.settrace(None)
                try:
                    assert (
                        client.post("/demo/replay-state", json=_demo("Luna", 700)).status_code
                        == 200
                    )
                finally:
                    threading.settrace(previous)
                assert main._get_demo_overlay_response()["hero"] == "Luna"
        finally:
            release.set()
            worker.join(5)
    assert not worker.is_alive() and not errors
    assert len(responses) == 1 and responses[0].status_code == 200
    overlay = client.get("/overlay/recommendation").json()
    if operation == "reset":
        assert not overlay.get("demo_mode") and overlay["status"] == "waiting_for_gsi"
        assert client.get("/session/memory").json()["hero"] is None
    else:
        assert overlay["demo_mode"] and overlay["hero"] == "Luna"
        assert overlay["simulated_timestamp_seconds"] == 700


def test_invalid_demo_and_reader_changes_do_not_change_cached_http_response(
    client: TestClient,
) -> None:
    assert client.post("/demo/replay-state", json=_demo()).status_code == 200
    before = client.get("/overlay/recommendation").json()
    response = main._get_demo_overlay_response()
    response["hero"] = "changed"
    response["recent_death_patterns"].append("changed")
    assert client.post("/demo/replay-state", json={"state": []}).status_code == 400
    assert client.get("/overlay/recommendation").json() == before
    assert client.get("/overlay/recommendation?lang=ru").status_code == 200
    assert client.get("/overlay/recommendation").json() == before


def test_cache_is_detached_and_expires_after_existing_eight_second_boundary() -> None:
    cache = DemoOverlayCache()
    response: dict[str, object] = {"hero": "Juggernaut", "items": [{"name": "TP"}]}
    token = cache.reserve()
    assert cache.publish(response, token, now=100)
    response["items"][0]["name"] = "changed"
    first = cache.capture(now=108)
    assert first == {"hero": "Juggernaut", "items": [{"name": "TP"}]}
    first["items"][0]["name"] = "changed"
    assert cache.capture(now=108)["items"][0]["name"] == "TP"
    assert cache.capture(now=108.001) is None
    assert not cache.publish(response, token, now=109)  # one request publishes only once
    assert cache.publish({"hero": "Luna"}, cache.reserve(), now=110)
    assert cache.capture(now=111) == {"hero": "Luna"}


def test_reset_window_invalidates_pending_and_overlapping_tokens_even_on_exception() -> None:
    cache = DemoOverlayCache()
    old = cache.reserve()
    assert cache.publish({"hero": "old"}, old, now=0)
    pending = cache.reserve()
    with pytest.raises(ValueError, match="reset failure"), cache.resetting():
        assert cache.capture(now=1) is None
        assert not cache.publish({"hero": "old"}, pending, now=1)
        during = cache.reserve()
        with cache.resetting():
            assert not cache.publish({"hero": "during"}, during, now=1)
            nested = cache.reserve()
        assert not cache.publish({"hero": "nested"}, nested, now=1)
        raise ValueError("reset failure")
    assert not cache.publish({"hero": "during"}, during, now=2)
    assert cache.publish({"hero": "fresh"}, cache.reserve(), now=2)
    assert cache.capture(now=3) == {"hero": "fresh"}


@pytest.mark.parametrize("operation", ["clear", "newer"])
def test_slow_actual_copy_does_not_block_invalidation_or_new_publication(operation: str) -> None:
    cache = DemoOverlayCache()
    response: dict[str, object] = {"hero": "old"}
    old = cache.reserve()
    entered, release = threading.Event(), threading.Event()
    results: list[bool] = []
    errors: list[Exception] = []
    original = threading.gettrace()

    def trace(frame: FrameType, event: str, _arg: Any) -> Any:
        if (
            event == "call"
            and frame.f_code is copy.deepcopy.__code__
            and frame.f_locals["x"] is response
        ):
            sys.settrace(None)
            entered.set()
            assert release.wait(5)
        return None

    def publish() -> None:
        try:
            results.append(cache.publish(response, old, now=0))
        except Exception as error:  # noqa: BLE001 - inspect real thread failure
            errors.append(error)

    threading.settrace(trace)
    worker = threading.Thread(target=publish)
    try:
        worker.start()
        assert entered.wait(5)
        if operation == "clear":
            cache.clear()
        assert cache.publish({"hero": "new"}, cache.reserve(), now=1)
    finally:
        threading.settrace(original)
        release.set()
        worker.join(5)
    assert not worker.is_alive() and not errors and results == [False]
    assert cache.capture(now=2) == {"hero": "new"}


def test_expiration_cannot_delete_a_new_concurrent_publication() -> None:
    cache = DemoOverlayCache()
    assert cache.publish({"hero": "expired"}, cache.reserve(), now=0)
    entered, watched, release, done = (threading.Event() for _ in range(4))
    original = threading.gettrace()
    results: dict[str, Any] = {}
    errors: list[Exception] = []

    def trace(frame: FrameType, event: str, _arg: Any) -> Any:
        if (
            event == "line"
            and frame.f_code is DemoOverlayCache.capture.__code__
            and frame.f_locals.get("frame") is not None
        ):
            sys.settrace(None)
            entered.set()
            assert release.wait(5)
        if event == "call" and frame.f_code is DemoOverlayCache.publish.__code__:
            watched.set()
        return trace if frame.f_code is DemoOverlayCache.capture.__code__ else None

    def expire() -> None:
        try:
            results["expired"] = cache.capture(now=9)
        except Exception as error:  # noqa: BLE001 - inspect real thread failure
            errors.append(error)

    def publish() -> None:
        try:
            # Reserve first, before the expiring read owns publication.
            results["published"] = cache.publish({"hero": "new"}, fresh, now=9)
        except Exception as error:  # noqa: BLE001 - inspect real thread failure
            errors.append(error)
        finally:
            done.set()

    fresh = cache.reserve()
    workers = [threading.Thread(target=expire), threading.Thread(target=publish)]
    threading.settrace(trace)
    try:
        workers[0].start()
        assert entered.wait(5)
        workers[1].start()
        assert watched.wait(5) and not done.wait(0.1)
    finally:
        threading.settrace(original)
        release.set()
        for worker in workers:
            if worker.ident is not None:
                worker.join(5)
    assert not any(worker.is_alive() for worker in workers) and not errors
    assert results == {"expired": None, "published": True}
    assert cache.capture(now=10) == {"hero": "new"}
