"""Independent single-executor queue with delayed retries and bounded shutdown."""

from __future__ import annotations

import heapq
import itertools
import threading
import time
from collections.abc import Callable

from app.diagnostics import record_error

# Combined queue join budget; launcher allows 8 seconds for backend shutdown.
# In-flight requests keep their provider timeouts and cannot be killed safely.
JOB_STOP_TIMEOUT_SECONDS = 3.0


class JobQueue:
    """One executor, delayed jobs, and deduplication through callback completion."""

    def __init__(
        self,
        *,
        auto_start: bool = True,
        clock: Callable[[], float] = time.monotonic,
        name: str = "player-jobs",
    ) -> None:
        self.auto_start = auto_start
        self.name = name
        self._clock = clock
        self._heap: list[tuple[float, int, str]] = []
        self._jobs: dict[str, Callable[[], None]] = {}
        self._counter = itertools.count()
        self._cond = threading.Condition()
        self._thread: threading.Thread | None = None
        self._running: str | None = None
        self._runner_id: int | None = None
        self._stopped = False

    def submit(self, key: str, fn: Callable[[], None], *, delay: float = 0.0) -> bool:
        """Accept one job, or reject a duplicate/stopped submission.

        A callback may schedule its own next attempt under the same key.
        Other callers cannot duplicate a running key.
        """
        with self._cond:
            if (
                self._stopped
                or key in self._jobs
                or (key == self._running and self._runner_id != threading.get_ident())
            ):
                return False
            self._jobs[key] = fn
            heapq.heappush(self._heap, (self._clock() + delay, next(self._counter), key))
            if self.auto_start:
                self._ensure_thread_locked()
            self._cond.notify_all()
            return True

    def pending(self) -> list[str]:
        """Outstanding keys, including the callback currently running."""
        with self._cond:
            keys = [self._running, *self._jobs] if self._running is not None else list(self._jobs)
            return list(dict.fromkeys(keys))

    def run_pending(self, *, until: float | None = None) -> int:
        """Run every job due by `until` (default: now). Returns how many ran."""
        ran = 0
        while True:
            with self._cond:
                limit = self._clock() if until is None else until
                if (
                    self._stopped
                    or self._running is not None
                    or not self._heap
                    or self._heap[0][0] > limit
                ):
                    return ran
                _, _, key = heapq.heappop(self._heap)
                fn = self._jobs.pop(key, None)
                if fn is not None:
                    self._running = key
                    self._runner_id = threading.get_ident()
            if fn is not None:
                try:
                    fn()
                    ran += 1
                finally:
                    with self._cond:
                        self._running = None
                        self._runner_id = None
                        self._cond.notify_all()

    def run_due(self, *, until: float | None = None) -> int:
        """Like run_pending, but a failing job is recorded for the problem report
        and the next jobs still run (the worker thread must never die)."""
        ran = 0
        while True:
            try:
                return ran + self.run_pending(until=until)
            except Exception as error:  # noqa: BLE001
                record_error(self.name, error)
                ran += 1

    def request_stop(self) -> None:
        """Reject submissions and discard queued work; let the active callback finish."""
        with self._cond:
            self._stopped = True
            self._jobs.clear()
            self._heap.clear()
            self._cond.notify_all()

    def stop(self, *, timeout: float = JOB_STOP_TIMEOUT_SECONDS) -> bool:
        """Wait outside the queue lock, within a real-time deadline.

        False means a callback/worker is still alive. Calling from the active
        callback only signals stop and returns False, without joining itself.
        """
        deadline = time.monotonic() + max(0.0, timeout)
        self.request_stop()
        with self._cond:
            if self._runner_id == threading.get_ident():
                return False
            thread = self._thread
        if thread is not None:
            thread.join(timeout=max(0.0, deadline - time.monotonic()))
        with self._cond:
            while self._running is not None:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return False
                self._cond.wait(timeout=remaining)
            return thread is None or not thread.is_alive()

    def _ensure_thread_locked(self) -> None:
        # submit holds the Condition across construction/start: no two workers.
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._loop, name=self.name, daemon=True)
        self._thread.start()

    def _loop(self) -> None:
        while True:
            with self._cond:
                if self._stopped:
                    return
                if self._running is not None:
                    self._cond.wait()
                    continue
                wait = None
                if self._heap:
                    wait = max(0.0, self._heap[0][0] - self._clock())
                if wait is None or wait > 0:
                    self._cond.wait(timeout=wait if wait is not None else 60)
                    continue
            self.run_due()
