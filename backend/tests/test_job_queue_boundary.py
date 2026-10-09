"""The queue can run independently; legacy imports keep the same queue class."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from app.job_queue import JOB_STOP_TIMEOUT_SECONDS, JobQueue
from app.player_service import JOB_STOP_TIMEOUT_SECONDS as LEGACY_STOP_TIMEOUT
from app.player_service import JobQueue as LegacyJobQueue

BACKEND = Path(__file__).resolve().parents[1]


def test_service_reexports_the_canonical_queue_and_deadline() -> None:
    assert LegacyJobQueue is JobQueue
    assert LEGACY_STOP_TIMEOUT == JOB_STOP_TIMEOUT_SECONDS


@pytest.mark.parametrize("auto_start", [True, False])
def test_fresh_queue_import_and_execution_need_no_player_http_sqlite_or_provider(
    tmp_path: Path, auto_start: bool
) -> None:
    script = """
import os
import sys
import threading
from pathlib import Path

os.environ['PLAYER_DATA_DIR'] = sys.argv[1]
from app.job_queue import JobQueue

assert len(threading.enumerate()) == 1, 'import started a worker'
assert not {
    'app.player_service', 'app.player_api', 'app.main', 'app.opendota',
    'app.coach_llm', 'sqlite3', 'fastapi',
}.intersection(sys.modules), 'queue crossed into service dependencies'
queue = JobQueue(auto_start=sys.argv[3] == 'true', name='independent-queue')
done = threading.Event()
def callback():
    Path(sys.argv[2]).write_text('executed', encoding='utf-8')
    done.set()
try:
    assert queue.submit('write', callback)
    if not queue.auto_start:
        assert queue.run_pending(until=float('inf')) == 1
    assert done.wait(5)
finally:
    assert queue.stop(timeout=5)
assert not Path(sys.argv[1]).exists(), 'queue import opened a player store'
assert len(threading.enumerate()) == 1, 'queue leaked a worker'
"""
    data_dir, marker = tmp_path / "unused-player-data", tmp_path / "callback.txt"
    result = subprocess.run(
        [sys.executable, "-c", script, str(data_dir), str(marker), str(auto_start).lower()],
        cwd=BACKEND,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=15,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert marker.read_text() == "executed" and not data_dir.exists()
