"""Durable finish delivery across SQLite/file faults, crashes and concurrent GSI."""

from __future__ import annotations

import json
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from match_fixtures import MATCH_ID, ME, gsi_match_stream

from app.local_api_auth import LOCAL_API_AUTH, LOCAL_API_URL
from app.main import app
from app.match_tracker import FINISH_RETRY_SECONDS, MatchTracker
from app.player_api import PLAYER_SERVICE
from app.player_service import PlayerService


def _stream(match_id: int = MATCH_ID) -> list[dict[str, Any]]:
    return gsi_match_stream(match_id=match_id, minutes=8, step_seconds=15, win=False)


def _journal(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _reject_writes(table: str, condition: str = "1") -> None:
    store = PLAYER_SERVICE.store
    with store._lock:
        store._conn.execute(
            f"CREATE TEMP TRIGGER reject_finish BEFORE INSERT ON {table} "
            f"WHEN {condition} BEGIN SELECT RAISE(ABORT, 'injected write failure'); END"
        )
        store._conn.commit()


def _allow_writes() -> None:
    store = PLAYER_SERVICE.store
    with store._lock:
        store._conn.rollback()
        store._conn.execute("DROP TRIGGER reject_finish")
        store._conn.commit()


def test_sqlite_failure_keeps_full_finish_and_startup_replays_it(client: TestClient) -> None:
    service = PLAYER_SERVICE
    stream = _stream()
    for payload in stream[:-1]:
        assert client.post("/gsi", json=payload).status_code == 200
    _reject_writes("matches")
    assert client.post("/gsi", json=stream[-1]).status_code == 200

    path = service.tracker.state_path
    pending = _journal(path)["pending"][0]
    assert pending["finished"] is True and pending["win"] is False
    assert pending["final"]["last_hits"] == 48
    assert pending["deaths"][0]["t"] == 7 * 60
    assert pending["samples"][0]["t"] == 0 and pending["samples"][-1]["t"] == 8 * 60
    diagnostics = client.get("/diagnostics").json()
    assert diagnostics["player"]["pending_match_finishes"] == 1
    assert diagnostics["errors"]["counts"]["match-finish"] >= 1
    _allow_writes()

    service.configure(service.data_dir, client=None, auto_start=False)
    assert service.store.count_matches(ME) == 1
    assert service.store.get_match(ME, MATCH_ID)["timeline"] == {
        key: value for key, value in pending.items() if not key.startswith("_")
    }
    assert not path.exists() and service.tracker.pending_count() == 0
    for lang in ("ru", "en"):
        detail = client.get(f"/player/matches/{MATCH_ID}?lang={lang}").json()
        assert detail["analysis"]["lang"] == lang
        assert detail["summary"]["win"] == 0


def test_partial_commit_replay_preserves_notes_and_enriched_match(client: TestClient) -> None:
    service = PLAYER_SERVICE
    _reject_writes("meta", "NEW.key LIKE 'last_review:%'")
    for payload in _stream():
        assert client.post("/gsi", json=payload).status_code == 200
    assert service.store.count_matches(ME) == 1
    assert service.tracker.pending_count() == 1
    _allow_writes()
    timeline = service.store.get_match(ME, MATCH_ID)["timeline"]
    assert service.store.set_note(ME, MATCH_ID, "Сохранённая заметка")
    service.store.upsert_match(
        ME, MATCH_ID, source="opendota", fields={"gpm": 999}, parse_status="parsed"
    )

    service.configure(service.data_dir, client=None, auto_start=False)
    row = service.store.get_match(ME, MATCH_ID)
    assert row["timeline"] == timeline
    assert row["note"] == "Сохранённая заметка"
    assert row["gpm"] == 999 and row["parse_status"] == "parsed"
    assert row["sources"] == ["gsi", "opendota"]
    assert service.store.count_matches(ME) == 1 and service.tracker.pending_count() == 0


@pytest.mark.parametrize("reason", ["post_game", "next_match", "stale"])
def test_failed_finish_retries_on_status_without_losing_next_match(
    tmp_path: Path, reason: str
) -> None:
    now = [0.0]
    delivered = []
    blocked = [True]

    def save(timeline: dict[str, Any]) -> None:
        if blocked[0]:
            raise OSError("store unavailable")
        delivered.append(timeline)

    tracker = MatchTracker(tmp_path / "live.json", on_finished=save, clock=lambda: now[0])
    stream = _stream()
    for payload in stream[:-1]:
        tracker.observe(payload)
    if reason == "post_game":
        tracker.observe(stream[-1])
    elif reason == "next_match":
        for payload in _stream(MATCH_ID + 1)[:10]:
            tracker.observe(payload)
    else:
        now[0] += 11 * 60
        tracker.check_stale()
    assert tracker.pending_count() == 1
    assert _journal(tracker.state_path)["pending"][0]["end_reason"] == reason
    blocked[0] = False
    now[0] += FINISH_RETRY_SECONDS
    tracker.check_stale()
    assert len(delivered) == 1 and delivered[0]["match_id"] == MATCH_ID
    if reason == "next_match":
        assert tracker.current()["match_id"] == MATCH_ID + 1
        restarted = MatchTracker(tracker.state_path)
        assert restarted.current()["match_id"] == MATCH_ID + 1
    else:
        assert tracker.current() is None and not tracker.state_path.exists()


def test_multiple_pending_finishes_survive_new_match_and_restart(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = PlayerService(tmp_path, auto_start=False)
    try:

        def unavailable(_timeline: dict[str, Any]) -> None:
            raise OSError("store unavailable")

        monkeypatch.setattr(service.tracker, "on_finished", unavailable)
        for match_id in (MATCH_ID, MATCH_ID + 1):
            for payload in _stream(match_id):
                service.observe_gsi(payload)
        for payload in _stream(MATCH_ID + 2)[:10]:
            service.observe_gsi(payload)
        journal = _journal(service.tracker.state_path)
        assert [entry["match_id"] for entry in journal["pending"]] == [MATCH_ID, MATCH_ID + 1]
        assert journal["current"]["match_id"] == MATCH_ID + 2

        service.configure(tmp_path, client=None, auto_start=False)
        assert service.store.count_matches(ME) == 2
        assert service.tracker.current()["match_id"] == MATCH_ID + 2
        assert service.tracker.pending_count() == 0
        assert _journal(service.tracker.state_path)["pending"] == []
    finally:
        service.shutdown()
        service.store.close()


@pytest.mark.parametrize("phase", ["write", "replace"])
def test_journal_fault_keeps_checkpoint_and_delays_callback_until_durable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, phase: str
) -> None:
    delivered = []
    tracker = MatchTracker(tmp_path / "live.json", on_finished=delivered.append)
    stream = _stream()
    for payload in stream[:-1]:
        tracker.observe(payload)
    tracker.flush()
    checkpoint = tracker.state_path.read_bytes()
    method = "open" if phase == "write" else "replace"
    original = getattr(Path, method)

    def fail(path: Path, *args: Any, **kwargs: Any) -> Any:
        if path == tracker.state_path.with_suffix(".tmp"):
            raise OSError("disk unavailable")
        return original(path, *args, **kwargs)

    with monkeypatch.context() as scoped:
        scoped.setattr(Path, method, fail)
        tracker.observe(stream[-1])
        assert delivered == [] and tracker.pending_count() == 1
        assert tracker.state_path.read_bytes() == checkpoint
    tracker.retry_pending(force=True)
    assert len(delivered) == 1 and delivered[0]["win"] is False
    assert delivered[0]["final"]["last_hits"] == 48
    assert not tracker.state_path.exists()


def test_failed_ack_replays_idempotently_after_restart(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = PLAYER_SERVICE
    path = service.tracker.state_path
    unlink = Path.unlink

    def fail_ack(target: Path, *args: Any, **kwargs: Any) -> Any:
        if target == path:
            raise OSError("ack unavailable")
        return unlink(target, *args, **kwargs)

    with monkeypatch.context() as scoped:
        scoped.setattr(Path, "unlink", fail_ack)
        for payload in _stream():
            assert client.post("/gsi", json=payload).status_code == 200
        assert service.store.count_matches(ME) == 1
        assert service.tracker.pending_count() == 1
        assert len(_journal(path)["pending"]) == 1
    service.configure(service.data_dir, client=None, auto_start=False)
    assert service.store.count_matches(ME) == 1
    assert service.tracker.pending_count() == 0 and not path.exists()


@pytest.mark.parametrize("after_commit", [False, True])
def test_real_process_crash_replays_before_or_after_database_commit(
    tmp_path: Path, after_commit: bool
) -> None:
    backend = Path(__file__).resolve().parents[1]
    code = """
import os
import sys
from pathlib import Path
sys.path.insert(0, 'tests')
from match_fixtures import gsi_match_stream
from app.player_service import PlayerService
service = PlayerService(Path(sys.argv[1]), auto_start=False)
save = service.tracker.on_finished
def crash(timeline):
    if sys.argv[2] == 'True':
        save(timeline)
    os._exit(73)
service.tracker.on_finished = crash
for payload in gsi_match_stream(minutes=8, step_seconds=15, win=False):
    service.observe_gsi(payload)
"""
    result = subprocess.run(
        [sys.executable, "-c", code, str(tmp_path), str(after_commit)],
        cwd=backend,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert result.returncode == 73, result.stderr
    pending = _journal(tmp_path / "live_match.json")["pending"][0]
    service = PlayerService(tmp_path, auto_start=False)
    try:
        row = service.store.get_match(ME, MATCH_ID)
        assert row["timeline"]["samples"] == pending["samples"]
        assert row["timeline"]["deaths"] == pending["deaths"]
        assert row["win"] == 0 and row["analysis"]
        assert service.store.count_matches(ME) == 1
        assert not service.tracker.state_path.exists()
    finally:
        service.shutdown()
        service.store.close()


def test_concurrent_finish_keeps_status_and_new_gsi_available(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = PLAYER_SERVICE
    entered, release = threading.Event(), threading.Event()
    errors = []
    save = service.tracker.on_finished

    def slow_save(timeline: dict[str, Any]) -> None:
        entered.set()
        assert release.wait(10), "test did not release finish callback"
        save(timeline)

    def finish(payload: dict[str, Any]) -> None:
        try:
            service.observe_gsi(payload)
        except Exception as error:  # noqa: BLE001 - assert thread result in parent
            errors.append(error)

    with TestClient(
        app, base_url=LOCAL_API_URL, headers=LOCAL_API_AUTH.headers, client=("127.0.0.1", 50000)
    ) as client:
        stream = _stream()
        for payload in stream[:-1]:
            assert client.post("/gsi", json=payload).status_code == 200
        monkeypatch.setattr(service.tracker, "on_finished", slow_save)
        worker = threading.Thread(target=finish, args=(stream[-1],))
        worker.start()
        try:
            assert entered.wait(5)
            assert client.get("/gsi/status").status_code == 200
            assert client.post("/gsi", json=_stream(MATCH_ID + 1)[0]).status_code == 200
            assert service.tracker.current()["match_id"] == MATCH_ID + 1
            assert service.tracker.pending_count() == 1
        finally:
            release.set()
            worker.join(timeout=10)
        assert not worker.is_alive() and not errors
        assert service.store.count_matches(ME) == 1 and service.tracker.pending_count() == 0
        assert _journal(service.tracker.state_path)["current"]["match_id"] == MATCH_ID + 1


def test_legacy_in_progress_file_still_recovers(tmp_path: Path) -> None:
    path = tmp_path / "live.json"
    tracker = MatchTracker(path)
    stream = _stream()
    for payload in stream[:15]:
        tracker.observe(payload)
    tracker.flush()
    path.write_text(json.dumps(_journal(path)["current"]), encoding="utf-8")
    delivered = []
    restarted = MatchTracker(path, on_finished=delivered.append)
    for payload in stream[15:]:
        restarted.observe(payload)
    assert len(delivered) == 1 and delivered[0]["samples"][0]["t"] == 0
    assert delivered[0]["win"] is False and not path.exists()


def test_finish_without_receiver_waits_for_acknowledgement(tmp_path: Path) -> None:
    path = tmp_path / "live.json"
    tracker = MatchTracker(path)
    for payload in _stream():
        tracker.observe(payload)
    assert tracker.current() is None and tracker.pending_count() == 1
    assert _journal(path)["pending"][0]["finished"] is True
    delivered = []
    restarted = MatchTracker(path, on_finished=delivered.append)
    restarted.check_stale()
    assert len(delivered) == 1 and delivered[0]["win"] is False
    assert restarted.pending_count() == 0 and not path.exists()
