# Live request work and the ASGI loop (0.53.41)

`POST /gsi` validates/authenticates its bounded packet in the existing middleware,
then runs preparation, normalization/owned enrichment, census, SQLite match
observation and recording through `run_in_threadpool`. `POST /demo/replay-state`
retains its async JSON/shape validation and runs observation, real scheduler/RAG,
logging, history and guarded publication through the same thread-pool boundary.
Responses and deterministic policy remain unchanged. Neither path performs its
sync filesystem/policy work on the ASGI event loop.

`LivePathMetrics` keeps at most 256 durations per fixed phase: GSI total,
preparation, policy, persistence, and demo total. Local `/diagnostics.live_path`
contains count, failed/running, latest, nearest-rank p50/p95, retained sample count
and observation time. Cold phases are null; a small sample is not a latency SLA.
The total includes nested phases, so their durations must not be summed with it.
Only fixed labels and timing numbers are retained. There is no automatic metrics
upload or background flush queue. The existing user-requested problem report
includes these aggregates in its preview and consent flow (site/privacy.html);
the metrics retain no GSI/account/advice content. Counter and
snapshot locks cover short in-memory operations; measured work executes outside
those locks. Exceptions decrement running and remain visible to their caller.
Handled recorder/player failures continue through existing diagnostics.

Six functional checks include four actual ASGI interleavings on the same event
loop: tracing pauses real preparation, memory policy, census persistence or demo
processing on its worker while `/health` still responds. They use real app,
authentication and HTTP transport. No internal function is replaced. Other checks
cover bounded/detached counters, exception cleanup and invalid demo input.
Existing GSI owner, cache, reset, replay and policy tests still apply.

This completes the audit's event-loop measurement/offload task. Thread-pool work
can still wait for its own resource/owner and does not make persistence bounded
by itself. The independently owned GSI, MatchMemory, scheduler and coach/demo
execution still need a whole-operation consistency boundary; F10 remains partial.

## Whole live operations (0.53.60, F10)

`app/live_operation.py` adds one outermost re-entrant lock over the in-memory
live owners. It is taken first, never while holding an owner's own lock:

- `POST /gsi`: the enrichment (MatchMemory, decision points) and publication of
  one packet (`update_latest_gsi`). The SQLite role prior is prepared before it;
  census, SQLite match observation and recordings run after it.
- `GET /overlay/recommendation`: snapshot read, MatchMemory, the scheduler's
  decision, the response and the coach session history (`_overlay_decision`).
  The advice log, the post-match note and the debug/match recordings run after
  it (`_record_advice_files`); map hints, the game plan and the death screen
  (SQLite reads) are added after it as before.
- `POST /demo/replay-state`: MatchMemory observation and the overlay response
  (developer-only; its recordings still run inside, as before).
- `POST /session/reset`: the whole reset.

So an overlay poll can no longer pair packet N's snapshot with MatchMemory
already moved to packet N+1, and a reset cannot land inside a packet.
`tests/test_live_operation.py` pauses a real packet inside MatchMemory with a
thread trace and proves that a poll and a reset wait for it (the poll test fails
without the lock), and that the advice log is written while the lock is free.
