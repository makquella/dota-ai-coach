"""Local operations health for the developer section and the problem report.

Answers "the advice came but the match was not saved" or "the AI hangs" at a
glance: background queue depth and ages, the live match's durable finish and
store acknowledgement, bounded live-path timings, and how fresh the bundled
and synced data are. Counts, ages and clock times only: no keys, job ids,
match data or advice text. `warnings` names what is off as stable codes the
launcher translates (renderer/app-texts.js `opsWarn_<code>`).
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

# A due job waiting this long means the single worker is stuck behind another.
QUEUE_WAIT_WARN_S = 120.0
# OpenDota/AI calls have their own timeouts well under this.
JOB_RUNNING_WARN_S = 300.0
# The GSI request's own work; Dota sends a packet every 0.1-0.5 s.
GSI_P95_WARN_MS = 250.0
# stratz-builds.yml refreshes the bundled builds weekly.
BUILDS_STALE_DAYS = 21


def _after(first: Any, second: Any) -> bool:
    """True when ISO time `first` is set and later than `second` (or `second` unset)."""
    return bool(first) and (not second or str(first) > str(second))


def _age_days(day: str | None, today: date) -> int | None:
    try:
        return (today - date.fromisoformat(str(day)[:10])).days if day else None
    except ValueError:
        return None


def build(
    *,
    jobs: dict[str, Any],
    ai_jobs: dict[str, Any],
    match_finish: dict[str, Any],
    sync: dict[str, Any],
    live_path: dict[str, Any],
    gsi_seconds_since: float | None,
    builds_generated: str | None,
    error_counts: dict[str, int],
    now: datetime | None = None,
) -> dict[str, Any]:
    now = now or datetime.now(UTC)
    warnings: list[str] = []
    for queue, prefix in ((jobs, "jobs"), (ai_jobs, "ai_jobs")):
        if (queue.get("oldest_due_s") or 0) >= QUEUE_WAIT_WARN_S:
            warnings.append(f"{prefix}_waiting")
        if (queue.get("running_for_s") or 0) >= JOB_RUNNING_WARN_S:
            warnings.append(f"{prefix}_running_long")
        if queue.get("queued") and not queue.get("worker_alive") and not queue.get("stopped"):
            warnings.append(f"{prefix}_no_worker")
    if match_finish.get("pending_finishes") and _after(
        match_finish.get("last_ack_error_at"), match_finish.get("last_ack_at")
    ):
        warnings.append("match_not_saved")
    if _after(match_finish.get("last_checkpoint_error_at"), match_finish.get("last_checkpoint_at")):
        warnings.append("recovery_write_failed")
    raw_phases = live_path.get("phases")
    phases: dict[str, dict[str, Any]] = {
        str(name): value
        for name, value in (raw_phases.items() if isinstance(raw_phases, dict) else [])
        if isinstance(value, dict)
    }
    persistence = phases.get("gsi.persistence", {})
    total = phases.get("gsi.total", {})
    if persistence.get("failed"):
        warnings.append("gsi_persistence_failed")
    if (total.get("p95_ms") or 0) >= GSI_P95_WARN_MS:
        warnings.append("gsi_slow")
    if sync.get("state") == "error":
        warnings.append("sync_failed")
    builds_age = _age_days(builds_generated, now.date())
    if builds_age is not None and builds_age > BUILDS_STALE_DAYS:
        warnings.append("builds_stale")
    return {
        "generated_at": now.isoformat(timespec="seconds"),
        "warnings": warnings,
        "queues": {"jobs": jobs, "ai_jobs": ai_jobs},
        "match_finish": match_finish,
        "live_path": {
            phase: {
                key: phases.get(phase, {}).get(key)
                for key in ("count", "failed", "running", "p50_ms", "p95_ms", "last_at")
            }
            for phase in ("gsi.total", "gsi.persistence")
        },
        "freshness": {
            "gsi_seconds_since": gsi_seconds_since,
            "sync_state": sync.get("state"),
            "sync_at": sync.get("at"),
            "builds_generated": builds_generated,
            "builds_age_days": builds_age,
        },
        "error_counts": dict(error_counts),
    }
