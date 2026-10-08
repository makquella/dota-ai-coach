"""Actual ASGI requests on one loop with real sync work paused by tracing."""

from __future__ import annotations

import asyncio
import sys
import threading
from types import FrameType
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient
from test_demo_overlay_cache import _demo
from test_gsi_snapshot import _packet

from app import main
from app.gsi_census import GsiCensus
from app.live_path_metrics import LIVE_PATH_METRICS, MAX_SAMPLES, LivePathMetrics
from app.local_api_auth import LOCAL_API_AUTH, LOCAL_API_URL


@pytest.mark.parametrize("phase", ["prepare", "policy", "persistence", "demo"])
def test_real_live_and_demo_work_does_not_block_the_asgi_event_loop(phase: str) -> None:
    targets = {
        "prepare": main._prepare_gsi_prior.__code__,
        "policy": main._observe_live_gsi.__code__,
        "persistence": GsiCensus.save_due.__code__,
        "demo": main._overlay_response_for_state.__code__,
    }
    entered, release = threading.Event(), threading.Event()
    worker_ids: list[int] = []
    original = threading.gettrace()

    def trace(frame: FrameType, event: str, _arg: Any) -> Any:
        if event == "call" and frame.f_code is targets[phase]:
            sys.settrace(None)
            worker_ids.append(threading.get_ident())
            entered.set()
            assert release.wait(5)
        return None

    async def exercise() -> None:
        loop_id = threading.get_ident()
        transport = httpx.ASGITransport(app=main.app, client=("127.0.0.1", 50000))
        async with httpx.AsyncClient(
            transport=transport, base_url=LOCAL_API_URL, headers=LOCAL_API_AUTH.headers
        ) as client:
            task = asyncio.create_task(
                client.post(
                    "/demo/replay-state" if phase == "demo" else "/gsi",
                    json=_demo() if phase == "demo" else _packet(),
                )
            )
            try:
                assert await asyncio.wait_for(asyncio.to_thread(entered.wait, 3), 4)
                assert len(worker_ids) == 1 and worker_ids[0] != loop_id
                assert not task.done()
                # Same app, transport and event loop while the real work is paused.
                health = await asyncio.wait_for(client.get("/health"), 1)
                assert health.status_code == 200 and health.json() == {"status": "ok"}
                assert not task.done()
            finally:
                release.set()
                response = await asyncio.wait_for(task, 4)
            assert response.status_code == 200
            body = response.json()
            assert (body["overlay"] if phase == "demo" else body["state"])["hero"] == "Juggernaut"
            debug = await client.get("/diagnostics")
            timing = debug.json()["live_path"]
            total = timing["phases"]["demo.total" if phase == "demo" else "gsi.total"]
            assert total["count"] >= 1 and total["running"] == 0
            assert total["latest_ms"] >= 0 and total["p95_ms"] >= total["p50_ms"]

    threading.settrace(trace)
    try:
        asyncio.run(exercise())
    finally:
        release.set()
        threading.settrace(original)


def test_timing_samples_are_bounded_detached_and_failures_release_running_count() -> None:
    metrics = LivePathMetrics()
    assert metrics.snapshot()["phases"]["gsi.total"]["p95_ms"] is None
    for _ in range(MAX_SAMPLES + 2):
        with metrics.measure("gsi.total"):
            pass
    with pytest.raises(ValueError, match="actual failure"), metrics.measure("gsi.total"):
        assert metrics.snapshot()["phases"]["gsi.total"]["running"] == 1
        raise ValueError("actual failure")
    snapshot = metrics.snapshot()
    total = snapshot["phases"]["gsi.total"]
    assert total["count"] == MAX_SAMPLES + 3
    assert total["sample_count"] == MAX_SAMPLES
    assert total["failed"] == 1 and total["running"] == 0 and total["last_at"]
    total["count"] = -1
    assert metrics.snapshot()["phases"]["gsi.total"]["count"] == MAX_SAMPLES + 3


def test_invalid_demo_does_not_enter_or_count_sync_processing(client: TestClient) -> None:
    before = LIVE_PATH_METRICS.snapshot()["phases"]["demo.total"]["count"]
    assert client.post("/demo/replay-state", json={"state": []}).status_code == 400
    assert (
        client.post(
            "/demo/replay-state", content=b"not JSON", headers={"Content-Type": "application/json"}
        ).status_code
        == 400
    )
    assert LIVE_PATH_METRICS.snapshot()["phases"]["demo.total"]["count"] == before
