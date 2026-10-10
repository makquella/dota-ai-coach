"""Real threads, queue retries and safe SQLite ownership during stop/configure."""

from __future__ import annotations

import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from match_fixtures import MATCH_ID, ME, FakeOpenDota, opendota_match

from app.job_queue import JobQueue
from app.local_api_auth import LOCAL_API_AUTH, LOCAL_API_URL
from app.main import app
from app.player_api import PLAYER_SERVICE
from app.player_service import PlayerService
from app.player_store import PlayerStore


def test_duplicate_running_key_is_rejected_until_callback_finishes() -> None:
    entered, release, done = threading.Event(), threading.Event(), threading.Event()
    queue = JobQueue()
    calls = []

    def slow() -> None:
        entered.set()
        assert release.wait(5)
        calls.append("original")

    try:
        assert queue.submit("same", slow)
        assert entered.wait(5)
        assert queue.pending() == ["same"]
        assert not queue.submit("same", lambda: calls.append("duplicate"))
        assert queue.submit("done", done.set)
        release.set()
        assert done.wait(5)
        assert queue.submit("same", lambda: calls.append("next"), delay=60)
    finally:
        release.set()
        assert queue.stop(timeout=5)
    assert calls == ["original"]
    assert queue.pending() == []


def test_running_callback_can_schedule_one_own_delayed_retry() -> None:
    entered, release, done = threading.Event(), threading.Event(), threading.Event()
    queue = JobQueue()
    calls = []

    def attempt() -> None:
        calls.append(len(calls) + 1)
        if len(calls) == 1:
            entered.set()
            assert release.wait(5)
            assert queue.submit("parse", attempt, delay=0.01)
            assert not queue.submit("parse", attempt)
            assert queue.pending() == ["parse"]
        else:
            done.set()

    try:
        assert queue.submit("parse", attempt)
        assert entered.wait(5)
        assert not queue.submit("parse", attempt)
        release.set()
        assert done.wait(5)
    finally:
        release.set()
        assert queue.stop(timeout=5)
    assert calls == [1, 2]


@pytest.mark.parametrize("auto_start", [False, True])
def test_stop_discards_due_and_delayed_jobs_and_rejects_new_work(auto_start: bool) -> None:
    entered, release = threading.Event(), threading.Event()
    # A frozen scheduling clock must not freeze the stop deadline.
    queue = JobQueue(auto_start=auto_start, clock=lambda: 0.0)
    calls = []

    def slow() -> None:
        entered.set()
        assert release.wait(5)
        calls.append("active")

    manual = None
    try:
        assert queue.submit("active", slow)
        if not auto_start:
            manual = threading.Thread(target=queue.run_due)
            manual.start()
        assert entered.wait(5)
        assert queue.submit("due", lambda: calls.append("due"))
        assert queue.submit("later", lambda: calls.append("later"), delay=60)
        started = time.monotonic()
        assert not queue.stop(timeout=0.02)
        assert time.monotonic() - started < 0.5
        assert queue.pending() == ["active"]
        assert not queue.submit("new", lambda: calls.append("new"))
        assert queue.run_due(until=float("inf")) == 0
    finally:
        release.set()
        if manual is not None:
            manual.join(timeout=5)
            assert not manual.is_alive()
        assert queue.stop(timeout=5)
    assert calls == ["active"]
    assert queue.pending() == []


def test_two_manual_runners_cannot_execute_callbacks_concurrently() -> None:
    entered, release = threading.Event(), threading.Event()
    queue = JobQueue(auto_start=False)
    calls = []

    def slow() -> None:
        entered.set()
        assert release.wait(5)
        calls.append("a")

    queue.submit("a", slow)
    queue.submit("b", lambda: calls.append("b"))
    runner = threading.Thread(target=queue.run_due)
    runner.start()
    try:
        assert entered.wait(5)
        assert queue.run_pending(until=float("inf")) == 0
        assert calls == []
    finally:
        release.set()
        runner.join(timeout=5)
        assert not runner.is_alive()
        assert queue.stop(timeout=5)
    assert calls == ["a", "b"]


def test_callback_can_signal_stop_without_joining_itself() -> None:
    queue = JobQueue(auto_start=False)
    results = []
    queue.submit("stop", lambda: results.append(queue.stop(timeout=5)))
    queue.submit("discard", lambda: results.append("must not run"))
    runner = threading.Thread(target=queue.run_due)
    runner.start()
    runner.join(timeout=5)
    assert not runner.is_alive() and results == [False]
    assert queue.stop(timeout=5)
    assert not queue.submit("late", lambda: None)


def test_exception_releases_running_key_and_worker_keeps_serving() -> None:
    queue = JobQueue()
    continued, retried = threading.Event(), threading.Event()

    def boom() -> None:
        raise RuntimeError("injected callback failure")

    try:
        queue.submit("failed", boom)
        queue.submit("continued", continued.set)
        assert continued.wait(5)
        assert queue.submit("failed", retried.set)
        assert retried.wait(5)
    finally:
        assert queue.stop(timeout=5)


def test_concurrent_first_submissions_create_one_worker(monkeypatch: pytest.MonkeyPatch) -> None:
    queue = JobQueue(name="one-worker-test")
    original_thread = threading.Thread
    constructing, release_constructor = threading.Event(), threading.Event()
    all_attempted, done = threading.Event(), threading.Event()
    guard = threading.Lock()
    workers, accepted, calls, errors = [], [], [], []
    attempts = [0]
    count = 12
    barrier = threading.Barrier(count)

    def thread_factory(*args: Any, **kwargs: Any) -> threading.Thread:
        worker = original_thread(*args, **kwargs)
        if kwargs.get("name") == queue.name:
            with guard:
                workers.append(worker)
            constructing.set()
            assert release_constructor.wait(5)
        return worker

    def job(index: int) -> None:
        with guard:
            calls.append(index)
            if len(calls) == count:
                done.set()

    def submit(index: int) -> None:
        try:
            barrier.wait(timeout=5)
            with guard:
                attempts[0] += 1
                if attempts[0] == count:
                    all_attempted.set()
            result = queue.submit(str(index), lambda: job(index))
            with guard:
                accepted.append(result)
        except Exception as error:  # noqa: BLE001 - propagate producer errors to parent
            errors.append(error)

    producers = [original_thread(target=submit, args=(index,)) for index in range(count)]
    with monkeypatch.context() as scoped:
        scoped.setattr(threading, "Thread", thread_factory)
        try:
            for producer in producers:
                producer.start()
            assert constructing.wait(5) and all_attempted.wait(5)
            release_constructor.set()
            for producer in producers:
                producer.join(timeout=5)
                assert not producer.is_alive()
            assert done.wait(5)
        finally:
            release_constructor.set()
            assert queue.stop(timeout=5)
    assert not errors and accepted == [True] * count
    assert len(workers) == 1 and sorted(calls) == list(range(count))


@pytest.mark.parametrize("queue_name", ["jobs", "ai_jobs"])
def test_configure_timeout_does_not_publish_or_close_a_new_store(
    tmp_path: Path, queue_name: str
) -> None:
    service = PlayerService(tmp_path / "old")
    original_store, original_client = service.store, service.client
    entered, release = threading.Event(), threading.Event()
    queue = getattr(service, queue_name)

    def old_job() -> None:
        entered.set()
        assert release.wait(5)
        service.store.set_meta("old-job", "old result")

    try:
        queue.submit("old-job", old_job)
        assert entered.wait(5)
        with pytest.raises(TimeoutError, match="store remains unchanged"):
            service.configure(tmp_path / "new", stop_timeout=0.02)
        assert service.store is original_store and service.client is original_client
        assert service.data_dir == tmp_path / "old" and not (tmp_path / "new").exists()
        assert original_store.get_meta("old-job") is None
        release.set()
        assert queue.stop(timeout=5)
        assert original_store.get_meta("old-job") == "old result"
        service.configure(tmp_path / "new")
        assert service.store.get_meta("old-job") is None
        with pytest.raises(sqlite3.ProgrammingError, match="closed"):
            original_store.get_meta("old-job")
    finally:
        release.set()
        assert service.shutdown(timeout=5)
        service.store.close()


@pytest.mark.parametrize("queue_name", ["jobs", "ai_jobs"])
def test_configure_waits_for_callback_before_closing_store(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, queue_name: str
) -> None:
    service = PlayerService(tmp_path / "old")
    original_store = service.store
    queue = getattr(service, queue_name)
    entered, release, stopping, finished = (
        threading.Event(),
        threading.Event(),
        threading.Event(),
        threading.Event(),
    )
    errors = []
    stop = queue.request_stop
    close = original_store.close

    def observe_stop() -> None:
        stop()
        stopping.set()

    def observe_close() -> None:
        assert finished.is_set(), "store closed before its old callback completed"
        close()

    def old_job() -> None:
        entered.set()
        assert release.wait(5)
        service.store.set_meta("old-job", "old result")
        finished.set()

    def configure() -> None:
        try:
            service.configure(tmp_path / "new", stop_timeout=5)
        except Exception as error:  # noqa: BLE001 - propagate control-thread errors
            errors.append(error)

    monkeypatch.setattr(queue, "request_stop", observe_stop)
    monkeypatch.setattr(original_store, "close", observe_close)
    controller = threading.Thread(target=configure)
    try:
        queue.submit("old-job", old_job)
        assert entered.wait(5)
        controller.start()
        assert stopping.wait(5)
        assert service.store is original_store and not (tmp_path / "new").exists()
        release.set()
        controller.join(timeout=5)
        assert not controller.is_alive() and not errors
        assert service.store.get_meta("old-job") is None
        persisted = PlayerStore(tmp_path / "old" / "coach.sqlite3")
        try:
            assert persisted.get_meta("old-job") == "old result"
        finally:
            persisted.close()
    finally:
        release.set()
        if controller.ident is not None:
            controller.join(timeout=5)
        assert service.shutdown(timeout=5)
        service.store.close()


def test_shutdown_signals_both_queues_and_shares_one_join_budget(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = PlayerService(tmp_path)
    release = threading.Event()
    entered = [threading.Event(), threading.Event()]
    observed = []
    stop = JobQueue.stop

    def old_job(index: int) -> None:
        entered[index].set()
        assert release.wait(5)
        service.store.set_meta(f"job:{index}", "result")

    def observe_stop(queue: JobQueue, *, timeout: float) -> bool:
        observed.append((queue.name, timeout))
        return stop(queue, timeout=timeout)

    try:
        for index, queue in enumerate((service.jobs, service.ai_jobs)):
            queue.submit("active", lambda index=index: old_job(index))
        assert all(event.wait(5) for event in entered)
        with monkeypatch.context() as scoped:
            scoped.setattr(JobQueue, "stop", observe_stop)
            started = time.monotonic()
            assert not service.shutdown(timeout=0.05)
            assert time.monotonic() - started < 0.5
        assert len(observed) == 2 and observed[1][1] < 0.02
        assert not service.jobs.submit("new", lambda: None)
        assert not service.ai_jobs.submit("new", lambda: None)
        assert service.store.get_meta("job:0") is None
        release.set()
        assert service.shutdown(timeout=5)
        assert service.shutdown(timeout=0)
        assert service.store.get_meta("job:0") == service.store.get_meta("job:1") == "result"
        old_store = service.store
        service.configure(tmp_path / "next")
        with pytest.raises(sqlite3.ProgrammingError, match="closed"):
            old_store.get_meta("job:0")
        persisted = PlayerStore(tmp_path / "coach.sqlite3")
        try:
            assert persisted.get_meta("job:0") == persisted.get_meta("job:1") == "result"
        finally:
            persisted.close()
    finally:
        release.set()
        assert service.shutdown(timeout=5)
        service.store.close()


def test_http_sync_deduplicates_running_fetch_and_lifespan_joins_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    entered, release, stopping = threading.Event(), threading.Event(), threading.Event()

    class BlockingClient(FakeOpenDota):
        attempts = 0

        def player(self, account_id: int) -> dict[str, Any]:
            self.attempts += 1
            entered.set()
            assert release.wait(5)
            return super().player(account_id)

    provider = BlockingClient()
    service = PLAYER_SERVICE
    service.configure(tmp_path / "svc", client=provider, auto_start=True)
    queue = service.jobs
    stop = queue.request_stop

    def observe_stop() -> None:
        stop()
        stopping.set()

    def release_on_stop() -> None:
        if stopping.wait(5):
            release.set()

    monkeypatch.setattr(queue, "request_stop", observe_stop)
    helper = threading.Thread(target=release_on_stop)
    try:
        with TestClient(
            app, base_url=LOCAL_API_URL, headers=LOCAL_API_AUTH.headers, client=("127.0.0.1", 50000)
        ) as client:
            assert client.post("/player/link", json={"steam": str(ME)}).status_code == 200
            assert entered.wait(5)
            for _ in range(5):
                response = client.post("/player/sync")
                assert response.status_code == 200
                assert response.json()["sync"]["state"] == "running"
            assert provider.attempts == 1
            assert f"sync:{ME}" in client.get("/diagnostics").json()["player"]["jobs"]
            helper.start()
        assert service.jobs.stop(timeout=0) and service.ai_jobs.stop(timeout=0)
        assert service.store.primary_account_id() == ME
        assert provider.attempts == 1
    finally:
        release.set()
        if helper.ident is not None:
            helper.join(timeout=5)
        assert service.shutdown(timeout=5)


def test_lifespan_timeout_keeps_store_usable_by_the_old_worker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = PLAYER_SERVICE
    entered, release = threading.Event(), threading.Event()
    service.configure(service.data_dir, auto_start=True)
    shutdown = service.shutdown
    result = []

    def old_job() -> None:
        entered.set()
        assert release.wait(5)
        service.store.set_meta("late-result", "saved in old store")

    def bounded_shutdown() -> bool:
        result.append(shutdown(timeout=0.02))
        return result[-1]

    try:
        with monkeypatch.context() as scoped:
            scoped.setattr(service, "shutdown", bounded_shutdown)
            with TestClient(
                app,
                base_url=LOCAL_API_URL,
                headers=LOCAL_API_AUTH.headers,
                client=("127.0.0.1", 50000),
            ) as client:
                service.jobs.submit("old-job", old_job)
                assert entered.wait(5)
                assert client.get("/health").status_code == 200
        assert result == [False]
        assert service.store.get_meta("late-result") is None
        release.set()
        assert service.jobs.stop(timeout=5)
        assert service.store.get_meta("late-result") == "saved in old store"
    finally:
        release.set()
        assert shutdown(timeout=5)


def test_inflight_http_question_can_save_after_queue_shutdown(tmp_path: Path) -> None:
    entered, release = threading.Event(), threading.Event()
    service = PLAYER_SERVICE
    responses, errors = [], []

    class BlockingLLM:
        label = {"provider": "test", "model": "test"}

        def complete(self, _messages: list[dict[str, str]], **_kwargs: Any) -> str:
            entered.set()
            assert release.wait(5)
            return json.dumps({"answer": "Зосередьтеся на безпечній грі."})

    service.configure(
        tmp_path,
        client=FakeOpenDota(matches={MATCH_ID: opendota_match(good=False)}),
        auto_start=False,
        llm=BlockingLLM(),
    )
    service.link(str(ME))
    service.fetch_match(MATCH_ID, request_parse=False)
    service.jobs.run_pending(until=float("inf"))

    with TestClient(
        app, base_url=LOCAL_API_URL, headers=LOCAL_API_AUTH.headers, client=("127.0.0.1", 50000)
    ) as client:

        def ask() -> None:
            try:
                responses.append(
                    client.post(
                        f"/player/matches/{MATCH_ID}/ask?lang=uk",
                        json={"question": "Як грати безпечніше?"},
                    )
                )
            except Exception as error:  # noqa: BLE001 - assert request-thread outcome
                errors.append(error)

        request = threading.Thread(target=ask)
        request.start()
        try:
            assert entered.wait(5)
            assert service.shutdown(timeout=0.02)
            assert not service.jobs.submit("late", lambda: None)
            release.set()
            request.join(timeout=5)
            assert not request.is_alive() and not errors
            assert len(responses) == 1 and responses[0].status_code == 200
            assert responses[0].json()["ok"] is True
            questions = client.get(f"/player/matches/{MATCH_ID}?lang=uk").json()["questions"]
            assert len(questions) == 1 and questions[0]["question"] == "Як грати безпечніше?"
        finally:
            release.set()
            request.join(timeout=5)


def test_completed_sync_does_not_get_stuck_queued_while_callback_returns(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = PLAYER_SERVICE
    service.configure(tmp_path, client=FakeOpenDota(), auto_start=True)
    service.store.set_primary(ME, source="test")
    completed, release = threading.Event(), threading.Event()
    sync = service._job_sync

    def completed_callback(account_id: int) -> None:
        sync(account_id)
        completed.set()
        assert release.wait(5)

    monkeypatch.setattr(service, "_job_sync", completed_callback)
    try:
        with TestClient(
            app, base_url=LOCAL_API_URL, headers=LOCAL_API_AUTH.headers, client=("127.0.0.1", 50000)
        ) as client:
            assert client.post("/player/sync").status_code == 200
            assert completed.wait(5)
            for _ in range(3):
                assert client.post("/player/sync").json()["sync"]["state"] == "done"
            assert service.jobs.pending()[0] == f"sync:{ME}"
            release.set()
            assert service.jobs.stop(timeout=5)
            assert client.get("/player").json()["sync"]["state"] == "done"
    finally:
        release.set()
        assert service.shutdown(timeout=5)


def test_rejected_sync_after_stop_keeps_its_previous_status(client: TestClient) -> None:
    service = PLAYER_SERVICE
    service.configure(service.data_dir, client=FakeOpenDota(), auto_start=False)
    service.store.set_primary(ME, source="test")
    service.jobs.request_stop()
    response = client.post("/player/sync")
    assert response.status_code == 200 and response.json()["sync"]["state"] == "idle"
    assert service.jobs.pending() == []
