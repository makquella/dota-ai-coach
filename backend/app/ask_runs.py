"""One provider run per AI coach question.

A question is answered synchronously, but the caller can lose the response (a
launcher timeout, a window reload) while the provider call goes on. The
launcher sends a `request_id` with every question; asking again with the same
id joins the run in progress or returns its stored result instead of spending
a second provider call, and `status` lets the launcher look the result up
later. The same question about the same match asked again while it runs (a
double click without an id) joins the run too. Finished runs are kept
in memory, at most KEEP_FINISHED of them; nothing here is persisted.
"""

from __future__ import annotations

import itertools
import threading
import time
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

KEEP_FINISHED = 32


@dataclass
class _Run:
    scope: str
    question: str
    started: float
    done: threading.Event = field(default_factory=threading.Event)
    result: dict[str, Any] | None = None
    waiters: int = 0


class AskRuns:
    def __init__(self, *, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._lock = threading.Lock()
        self._runs: OrderedDict[str, _Run] = OrderedDict()
        self._anonymous = itertools.count()

    def run(
        self,
        scope: str,
        question: str,
        request_id: str | None,
        work: Callable[[], dict[str, Any]],
        *,
        wait_s: float,
    ) -> dict[str, Any]:
        """`work()` once per request id (or per scope + question while it runs)."""
        question = " ".join(str(question or "").split()).lower()
        with self._lock:
            run = self._runs.get(request_id) if request_id else None
            if run is not None and run.scope != scope:
                return {"ok": False, "code": "bad_request"}
            if run is None:
                run = next(
                    (
                        other
                        for other in self._runs.values()
                        if not other.done.is_set()
                        and other.scope == scope
                        and other.question == question
                    ),
                    None,
                )
            owner = run is None
            if run is None:
                run = _Run(scope=scope, question=question, started=self._clock())
                self._runs[request_id or f"anonymous:{next(self._anonymous)}"] = run
                self._prune_locked()
            else:
                run.waiters += 1
        if not owner:
            finished = run.done.wait(wait_s)
            with self._lock:
                run.waiters -= 1
            if not finished:
                return {"ok": False, "code": "pending", "request_id": request_id}
            return dict(run.result or {"ok": False, "code": "bad_response"})
        result: dict[str, Any] = {"ok": False, "code": "bad_response"}
        try:
            result = work()
        finally:
            with self._lock:
                run.result = result
                run.done.set()
        return result

    def status(self, request_id: str) -> dict[str, Any]:
        with self._lock:
            run = self._runs.get(request_id)
            if run is None:
                return {"state": "unknown"}
            if not run.done.is_set():
                return {
                    "state": "running",
                    "elapsed_s": round(self._clock() - run.started, 1),
                    "waiters": run.waiters,
                }
            return {"state": "done", "result": dict(run.result or {})}

    def running(self) -> int:
        with self._lock:
            return sum(1 for run in self._runs.values() if not run.done.is_set())

    def _prune_locked(self) -> None:
        finished = [key for key, run in self._runs.items() if run.done.is_set()]
        for key in finished[: max(0, len(finished) - KEEP_FINISHED)]:
            del self._runs[key]
