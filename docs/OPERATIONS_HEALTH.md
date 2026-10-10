# Local operations health (0.53.51)

`GET /operations/health` (control token required) and `/diagnostics`
`operations` answer "advice came but the match was not saved" or "the AI coach
hangs" without reading logs. `app/operations_health.py` builds it from
snapshots its owners already keep; it holds no state of its own.

- **Queues** (`JobQueue.health`, history `player-jobs` and `coach-ai`): queued,
  due, the oldest due job's wait, the next delayed job, the running job's kind
  (the key before `:`, never an account or match id) and how long it runs,
  completed/failed counts and times, worker alive, stopped.
- **Match saving** (`MatchTracker.health`): finished matches waiting for the
  store, the retry delay, and the last recovery-file checkpoint and store
  acknowledgement with their last failures.
- **Live path**: `LIVE_PATH_METRICS` counts, failures and p50/p95 for
  `gsi.total` and `gsi.persistence` (bounded to 256 samples per phase).
- **Freshness**: seconds since the last GSI packet, the last OpenDota sync state
  and time, the bundled STRATZ builds' date and age.

`warnings` are stable codes with thresholds in the module: a due job waiting
2 minutes, a job running 5 minutes, jobs queued without a worker, a pending
finish whose last store attempt failed after the last success, a failed
recovery checkpoint newer than the last good one, any failed GSI persistence,
GSI p95 at 250 ms or more, a failed sync, builds older than 21 days. A later
success clears a save warning.

The launcher's developer section shows it as «Стан операцій» / «Operations
health» (`renderer/ops-health.js`, copy `ops*` in `app-texts.js`): read when the
section opens, on «Оновити» and every 10 s while it stays open and the window
is visible. Unknown codes from a newer backend show as the code.

Tests: `backend/tests/test_operations_health.py` (fake-clock queue, every
warning, a real refused SQLite finish through `/gsi`, the token),
`frontend/launcher/test/ops-health.test.js` (UK/EN lines and every code).
