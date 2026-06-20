"""
logger.py — writes one JSON log file per recommendation request.

Files are stored in backend/logs/ with a timestamp-based name.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from app.config import LOGS_DIR
from app.schemas import GameSituationRequest, RecommendationResponse


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

    timestamp = datetime.now(timezone.utc).isoformat()
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
    return log_path
