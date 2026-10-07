# Recovery of live matches

From 0.53.4, `PLAYER_DATA_DIR/live_match.json` is an internal recovery journal:
`recovery_version: 1`, `current` (the ongoing timeline or null) and `pending`
(finished timelines awaiting acknowledgement). It is local, optional raw
recordings are independent, and no recovery data is uploaded. The tracker also
reads the plain in-progress timeline written by 0.53.3 and earlier.

When a reviewable match ends through POST_GAME, a new match ID or stale GSI,
the tracker records its finish reason, final observations and known result in
`pending`. It writes a temporary file, flushes/fsyncs it and replaces the journal
before calling the receiver. A new match shares the journal with pending older
matches, so its checkpoints cannot overwrite them. Short games and games
without a seen hero still do not produce a review.

The receiver stores by SQLite's existing `(account_id, match_id)` primary key.
If the same timeline is already stored, replay resumes analysis/metadata work
without overwriting enriched summary fields, parse status or the player's note.
Only a successful callback removes the pending entry; the journal is removed
when neither an ongoing match nor pending deliveries remain. A crash after the
DB commit but before acknowledgement can replay the callback safely.

PlayerService retries loaded pending finishes after all its state is initialized.
GSI and `/gsi/status` retry thereafter, with a five-second delay after failures;
shutdown and backup flush request an immediate retry. Callback delivery has a
separate lock, outside the tracker's state lock, so concurrent status/GSI calls
do not deliver the same pending batch simultaneously. This does not change the
background JobQueue lifetime or deduplication rules (audit F02 remains open).

Errors are recorded as `match-recovery` (journal I/O) or `match-finish` (receiver).
Problem reports expose `player.pending_match_finishes` as a count, without raw
timeline contents. If the journal cannot be written, delivery waits, RAM keeps
the pending finish and the previous on-disk checkpoint remains available. A
restart during a persistent journal write failure can only recover that earlier
checkpoint; observations that no storage accepted cannot be promised durable.
Recovery tests cover process termination, not hardware/power-loss guarantees.

`TIMELINE_VERSION`, `ANALYSIS_VERSION` and `TRIM_VERSION` remain unchanged:
only the internal recovery envelope changes, not stored match facts or review
rules. Do not edit the journal by hand or include it in public diagnostic files.
An older app version does not understand the new envelope; let pending finishes
complete before downgrading. History already saved in SQLite stays compatible.

Validation from `backend/`:

```bash
python -m pytest tests/test_match_finish_recovery.py tests/test_player_history.py tests/test_history_backup.py tests/test_match_notes.py tests/test_match_advice_log.py
```

The recovery suite uses real SQLite write-failure triggers, file I/O faults,
subprocess crashes before/after commit, concurrent threads/Events with a
context-managed TestClient, legacy files, multiple pending matches and both
localized review responses. Windows build/installer smoke checks the frozen
runtime on the target platform.
