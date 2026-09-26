"""
logger.py — writes one JSON log file per recommendation request.

Files are stored in backend/logs/ with a timestamp-based name. Only the
newest KEEP_LOG_FILES are kept (a match writes a few dozen; months of play
would otherwise leave tens of thousands of files in %APPDATA%).
"""

import json
from datetime import UTC, datetime
from pathlib import Path

from app.config import LOGS_DIR
from app.schemas import GameSituationRequest, RecommendationResponse

KEEP_LOG_FILES = 500
PRUNE_EVERY = 50
_writes = 0


def prune_logs(logs_dir: Path | None = None, keep: int = KEEP_LOG_FILES) -> int:
    """Delete all but the newest `keep` recommendation logs; returns how many went."""
    folder = logs_dir or LOGS_DIR
    try:
        files = sorted(folder.glob("*.json"))  # names start with an ISO timestamp
    except OSError:
        return 0
    removed = 0
    for path in files[: max(0, len(files) - keep)]:
        try:
            path.unlink()
            removed += 1
        except OSError:
            pass
    return removed


def log_recommendation(
    request: GameSituationRequest,
    rag_context: list[str],
    response: RecommendationResponse,
    decision_point: str | None = None,
    provider: str = "fallback",
    model: str | None = None,
    llm_error: str | None = None,
    fallback_reason: str | None = None,
) -> Path:
    """
    Persist a single request/response pair as a JSON file.
    Returns the path of the written file.
    """
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(UTC).isoformat()
    # Build a filename that is easy to sort chronologically
    safe_ts = timestamp.replace(":", "-").replace("+", "Z")
    filename = f"{safe_ts}_{request.hero.replace(' ', '_')}.json"

    log_entry = {
        "timestamp": timestamp,
        "input": request.model_dump(),
        "decision_point": decision_point,
        "rag_context": rag_context,
        "provider": provider,
        "model": model,
        "source": response.source,
        "output": response.model_dump(),
    }
    if llm_error:
        log_entry["llm_error"] = llm_error
    if fallback_reason:
        log_entry["fallback_reason"] = fallback_reason

    log_path = LOGS_DIR / filename
    log_path.write_text(json.dumps(log_entry, indent=2, ensure_ascii=False), encoding="utf-8")
    global _writes
    _writes += 1
    if _writes % PRUNE_EVERY == 0:
        prune_logs()
    return log_path
