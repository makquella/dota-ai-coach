"""Real filesystem failures retain acknowledgements and live HTTP responses."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient
from test_gsi_snapshot import _packet

from app.atomic_file import write_json_atomic
from app.diagnostics import recent_errors
from app.gsi_census import GsiCensus
from app.live_session_recorder import LIVE_SESSION_RECORDER, LiveSessionRecorder
from app.match_records import MatchRecords


def test_census_failed_replacement_is_not_acknowledged_and_retries_without_new_packet(
    tmp_path: Path,
) -> None:
    census = GsiCensus()
    census.observe(_packet())
    path = tmp_path / "census.json"
    path.mkdir()  # real replacement failure on both Windows and Unix
    assert not census.save_due(path, now=1000)
    health = census.summary()["persistence"]
    assert health["acknowledged_in_game"] == 0 and health["failures"] == 1
    assert not health["pending"] and health["last_error"]
    path.rmdir()
    assert not census.save_due(path, now=1004)  # bounded failure retry
    assert census.summary()["persistence"]["failures"] == 1
    assert census.save_due(path, now=1005)  # same observed packet, actual disk ack
    assert json.loads(path.read_text())["in_game_payloads"] == 1
    health = census.summary()["persistence"]
    assert health["acknowledged_in_game"] == 1 and health["last_error"] is None
    assert not census.save_due(path, now=2000)
    assert not list(tmp_path.glob(".wardly-*.tmp"))


def test_atomic_json_failed_encoding_preserves_existing_file(tmp_path: Path) -> None:
    path = tmp_path / "metadata.json"
    write_json_atomic(path, {"saved": 1})
    try:
        write_json_atomic(path, {"unsafe": float("nan")})
    except ValueError:
        pass
    else:
        raise AssertionError("Non-finite metadata must fail before file replacement")
    assert json.loads(path.read_text()) == {"saved": 1}
    assert not list(tmp_path.glob(".wardly-*.tmp"))


def test_recorder_start_and_append_failures_stop_optional_io_and_keep_real_counts(
    tmp_path: Path,
) -> None:
    blocked = tmp_path / "blocked"
    blocked.write_text("file blocks mkdir")
    recorder = LiveSessionRecorder(blocked)
    status = recorder.start()
    assert (
        not status["active"]
        and status["failures"] == 1
        and status["last_error"].startswith("start:")
    )
    recorder = LiveSessionRecorder(tmp_path / "recordings")
    status = recorder.start()
    folder = Path(status["session_dir"])
    (folder / "raw_gsi_states.jsonl").mkdir()
    recorder.record_gsi(_packet(), {"hero": "Juggernaut"})
    assert not recorder.health()["active"] and recorder.health()["gsi_count"] == 0
    assert recorder.health()["failures"] == 1
    recorder.record_gsi(_packet(), {"hero": "Juggernaut"})
    assert recorder.health()["failures"] == 1  # no failing write for every packet
    first = folder
    restarted = recorder.start()
    assert restarted["active"] and Path(restarted["session_dir"]) != first
    recorder.stop()


def test_written_jsonl_count_survives_metadata_failure_without_truncating_previous_file(
    tmp_path: Path,
) -> None:
    recorder = LiveSessionRecorder(tmp_path)
    status = recorder.start()
    folder = Path(status["session_dir"])
    metadata = folder / "metadata.json"
    initial = metadata.read_bytes()
    metadata.rename(folder / "saved-metadata.json")
    metadata.mkdir()
    recorder.record_gsi(_packet(), {"hero": "Juggernaut"})
    assert recorder.health()["gsi_count"] == 1 and not recorder.health()["active"]
    assert recorder.health()["last_error"].startswith("metadata:")
    assert len((folder / "raw_gsi_states.jsonl").read_text().splitlines()) == 1
    assert (folder / "saved-metadata.json").read_bytes() == initial
    assert not list(folder.glob(".wardly-*.tmp"))


def test_actual_http_gsi_and_advice_survive_real_recorder_write_failure(
    client: TestClient, tmp_path: Path
) -> None:
    original = LIVE_SESSION_RECORDER.base_dir
    LIVE_SESSION_RECORDER.stop()
    LIVE_SESSION_RECORDER.base_dir = tmp_path
    try:
        started = client.post("/session-recording/start").json()
        (Path(started["session_dir"]) / "raw_gsi_states.jsonl").mkdir()
        response = client.post("/gsi", json=_packet())
        assert response.status_code == 200 and response.json()["state"]["hero"] == "Juggernaut"
        assert client.get("/overlay/recommendation").status_code == 200
        health = client.get("/diagnostics").json()["recording_health"]["live_session"]
        assert not health["active"] and health["last_error"] and health["gsi_count"] == 0
        assert client.get("/health").json() == {"status": "ok"}
    finally:
        LIVE_SESSION_RECORDER.stop()
        LIVE_SESSION_RECORDER.base_dir = original


def test_match_record_failure_is_reported_with_unconfirmed_lines_and_bounded_buffer(
    tmp_path: Path,
) -> None:
    recorder = MatchRecords()
    recorder.configure(tmp_path, enabled=True)
    recorder.record_gsi(_packet(), now=1000)
    assert recorder._path is not None
    recorder._path.mkdir()  # real gzip append error; no internal function replacement
    recorder.flush()
    health = recorder.health()
    assert health["failures"] == 1 and health["last_error"]
    assert health["unconfirmed_lines"] >= 1 and health["buffered_lines"] == 0
    assert recent_errors()["counts"]["match-records-flush"] >= 1
