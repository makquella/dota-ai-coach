# Background job lifetime

From 0.53.5, `JobQueue` protects queued keys, its running key and worker creation
with one `Condition`. A key remains outstanding through callback completion.
`submit()` returns false for a queued duplicate, an external duplicate of a
running key or a stopped queue. Only the current callback may schedule one next
attempt under its own running key; this preserves OpenDota parsing retries.
AI busy retries with their existing distinct keys are unchanged.

There is one callback executor even when a manual `run_pending()`/`run_due()`
call overlaps the daemon worker. The running key is released in `finally`, so a
failure does not leave it blocked. Background exceptions still go to diagnostics
and later jobs continue. `pending()` includes the running key once, which keeps
friend loading and problem-report counts accurate during network requests.
Sync status transitions share a lock: rejected duplicates preserve the actual
running/done state rather than leaving the UI "queued" after completion.

`request_stop()` atomically rejects new work, discards queued/delayed callbacks
and wakes the worker. It lets the active callback finish. `stop(timeout=...)`
joins outside the Condition, using a real monotonic deadline independent of
the scheduling clock, and also waits for a manually run active callback.
It returns true only when the queue is quiescent. A callback stopping its own
queue signals stop and returns false rather than joining itself.

PlayerService signals both OpenDota and AI queues before joining either. They
share a **three-second join budget**, not three seconds each. The launcher
allows eight seconds for backend exit and Uvicorn allows three seconds for
in-flight requests; local tracker flush/SQLite operations additionally take
their normal I/O time. The join budget does not interrupt a requests call:
OpenDota retains its existing `(10, 60)` connect/read timeouts and one timeout
retry, and AI retains its existing per-attempt timeouts/fallbacks. End-to-end
provider cancellation/deadlines are separate work; no instant cancellation is
promised.

`configure(stop_timeout=...)` serializes with shutdown and refuses to replace
service state while an old callback/worker is alive. On timeout it raises
`TimeoutError` before closing SQLite or changing data_dir/client/store; both
queues remain stopped. The old callback can finish using its old service/store.
Retry configure after it finishes. Once queues are quiescent, configure flushes
the old tracker, closes the old store and initializes the new state. Therefore
an old queue callback cannot reach the next store through `self`. Configure is
startup/test setup; its caller must also quiesce unrelated HTTP writers before
reconfiguration.

`shutdown(timeout=...)` first stops submissions, flushes tracker recovery and
joins both queues. On success it is idempotent; on timeout it returns false and
records `player-lifecycle` diagnostics. SQLite keeps its existing process
lifetime: synchronous HTTP writers (such as AI questions) are outside JobQueue
and may outlive ASGI cancellation, so queue shutdown does not close their
connection. A later safe configure closes it, or process exit releases it.
Daemon threads do not keep
the backend process alive after its shutdown budget. Delayed jobs are not a
persistent queue: startup/user polling can request work again, as before.

The internal lifecycle lock serializes configure/shutdown; it does not make all
HTTP state updates atomic. Snapshot ownership (F10), backup transactionality
(F03), and end-to-end AI request deadlines remain separate audit tasks.
SQLite schema, timeline/recovery formats and analysis rules are unchanged.

Validation from `backend/`:

```bash
python -m pytest tests/test_job_queue_lifecycle.py tests/test_player_history.py tests/test_coach_ai.py tests/test_diagnostics.py tests/test_match_finish_recovery.py
```

Tests use actual threads and Events rather than sleep ordering, real SQLite
stores and context-managed FastAPI TestClient lifespans. They cover duplicates,
owner retries, concurrent worker creation/manual execution, self-stop, exception
recovery, delayed-work cancellation, shared deadlines, rejected/waiting store
reconfiguration and shutdown before/after provider completion. HTTP sync tests
use a blocking fake OpenDota provider; a blocking fake AI provider verifies
question-history writes after queue shutdown. No live provider calls are required.
