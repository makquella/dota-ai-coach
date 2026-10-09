"""Local operations health: queue depth/ages, match saving acks, live-path
timings and data freshness, for the developer section and the problem report."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from match_fixtures import MATCH_ID, gsi_match_stream

from app import operations_health
from app.job_queue import JobQueue
from app.player_api import PLAYER_SERVICE


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def test_queue_health_counts_waiting_running_and_failed_jobs():
    clock = FakeClock()
    queue = JobQueue(auto_start=False, clock=clock, name="test-jobs")
    seen: list[dict] = []
    queue.submit("sync:123456789", lambda: seen.append(queue.health()))
    queue.submit("later:1", lambda: None, delay=60)
    clock.now += 30
    health = queue.health()
    assert health["queued"] == 2 and health["due"] == 1
    assert health["oldest_due_s"] == 30.0 and health["next_in_s"] == 30.0
    assert health["running"] is False and health["worker_alive"] is False

    assert queue.run_pending() == 1
    # While a job runs, only its kind shows (never an account or match id).
    assert seen[0]["running"] is True and seen[0]["running_kind"] == "sync"
    assert "123456789" not in str(seen[0])
    health = queue.health()
    assert health["completed"] == 1 and health["failed"] == 0
    assert health["last_finished_at"] and health["last_failed_at"] is None

    def boom() -> None:
        raise RuntimeError("provider down")

    queue.submit("ai:1", boom)
    assert queue.run_due() == 1
    health = queue.health()
    assert health["failed"] == 1 and health["last_failed_at"]
    assert health["queued"] == 1  # the delayed job still waits


def _build(**overrides):
    idle = {
        "queued": 0,
        "due": 0,
        "oldest_due_s": None,
        "running_for_s": None,
        "worker_alive": True,
    }
    values = {
        "jobs": dict(idle),
        "ai_jobs": dict(idle),
        "match_finish": {"pending_finishes": 0},
        "sync": {"state": "done", "at": "2026-10-09T10:00:00+00:00"},
        "live_path": {"phases": {"gsi.total": {"p95_ms": 12.0}, "gsi.persistence": {"failed": 0}}},
        "gsi_seconds_since": 3.0,
        "builds_generated": "2026-10-06",
        "error_counts": {},
        "now": datetime(2026, 10, 9, 12, tzinfo=UTC),
    }
    values.update(overrides)
    return operations_health.build(**values)


def test_a_healthy_app_has_no_warnings():
    health = _build()
    assert health["warnings"] == []
    assert health["freshness"]["builds_age_days"] == 3
    assert health["live_path"]["gsi.total"]["p95_ms"] == 12.0


@pytest.mark.parametrize(
    ("overrides", "warning"),
    [
        ({"jobs": {"queued": 1, "oldest_due_s": 150, "worker_alive": True}}, "jobs_waiting"),
        (
            {"ai_jobs": {"queued": 1, "running_for_s": 400, "worker_alive": True}},
            "ai_jobs_running_long",
        ),
        ({"jobs": {"queued": 2, "worker_alive": False, "stopped": False}}, "jobs_no_worker"),
        (
            {
                "match_finish": {
                    "pending_finishes": 1,
                    "last_ack_at": "2026-10-09T10:00:00+00:00",
                    "last_ack_error_at": "2026-10-09T11:00:00+00:00",
                }
            },
            "match_not_saved",
        ),
        (
            {"match_finish": {"last_checkpoint_error_at": "2026-10-09T11:00:00+00:00"}},
            "recovery_write_failed",
        ),
        ({"live_path": {"phases": {"gsi.persistence": {"failed": 2}}}}, "gsi_persistence_failed"),
        ({"live_path": {"phases": {"gsi.total": {"p95_ms": 300}}}}, "gsi_slow"),
        ({"sync": {"state": "error"}}, "sync_failed"),
        ({"builds_generated": "2026-08-01"}, "builds_stale"),
    ],
)
def test_each_problem_has_its_warning(overrides, warning):
    assert _build(**overrides)["warnings"] == [warning]


def test_a_later_successful_save_clears_the_warning():
    health = _build(
        match_finish={
            "pending_finishes": 0,
            "last_checkpoint_at": "2026-10-09T11:30:00+00:00",
            "last_checkpoint_error_at": "2026-10-09T11:00:00+00:00",
            "last_ack_at": "2026-10-09T11:30:00+00:00",
            "last_ack_error_at": "2026-10-09T11:00:00+00:00",
        }
    )
    assert health["warnings"] == []


def test_endpoint_reports_a_finish_the_store_refused(client: TestClient):
    stream = gsi_match_stream(match_id=MATCH_ID, minutes=8, step_seconds=15, win=False)
    for payload in stream[:-1]:
        assert client.post("/gsi", json=payload).status_code == 200
    store = PLAYER_SERVICE.store
    with store._lock:
        store._conn.execute(
            "CREATE TEMP TRIGGER reject_finish BEFORE INSERT ON matches "
            "BEGIN SELECT RAISE(ABORT, 'injected write failure'); END"
        )
        store._conn.commit()
    try:
        assert client.post("/gsi", json=stream[-1]).status_code == 200
        health = client.get("/operations/health").json()
    finally:
        with store._lock:
            store._conn.rollback()
            store._conn.execute("DROP TRIGGER reject_finish")
            store._conn.commit()
    assert "match_not_saved" in health["warnings"]
    finish = health["match_finish"]
    assert finish["pending_finishes"] == 1 and finish["last_ack_error_at"]
    assert finish["last_checkpoint_at"] and finish["last_checkpoint_error_at"] is None
    assert health["live_path"]["gsi.total"]["count"] >= len(stream)
    assert health["queues"]["jobs"]["name"] == "player-jobs"
    assert health["queues"]["ai_jobs"]["name"] == "coach-ai"
    assert client.get("/diagnostics").json()["operations"]["warnings"] == health["warnings"]


def test_endpoint_needs_the_launcher_token(client: TestClient):
    assert client.get("/operations/health", headers={"Authorization": ""}).status_code == 401
