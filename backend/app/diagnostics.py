"""
diagnostics.py - what went wrong recently, for the tester's problem report.

Background jobs (OpenDota sync, AI coach) and the GSI side path swallow their
errors so the app keeps working; they record them here instead. The launcher's
"Problem report" button saves `GET /diagnostics` together with its own log.
Nothing here contains keys: messages are redacted before they are stored.
"""

from __future__ import annotations

import platform
import re
import sys
import threading
import time
import traceback
from collections import deque
from datetime import UTC, datetime
from typing import Any

MAX_ERRORS = 50
STARTED_AT = time.time()

# Gemini (AIza…, AQ.…), Groq (gsk_…), OpenRouter (sk-or-…), bearer tokens and
# ?api_key=… in URLs (OpenDota).
_SECRET_RE = re.compile(
    r"(AIza[\w-]{20,}|AQ\.[\w-]{20,}|gsk_[\w-]{16,}|sk-[\w-]{16,}|Bearer\s+[\w.-]{12,}"
    r"|(?<=api_key=)[^&\s'\"]+)"
)

_lock = threading.Lock()
_errors: deque[dict[str, Any]] = deque(maxlen=MAX_ERRORS)
_counts: dict[str, int] = {}


def redact(text: Any) -> str:
    return _SECRET_RE.sub("[redacted]", str(text))


def record_error(scope: str, error: BaseException | str, *, with_trace: bool = True) -> None:
    """Keep the last MAX_ERRORS errors (newest last); never raises."""
    try:
        if isinstance(error, BaseException):
            message = f"{type(error).__name__}: {error}"
            trace = (
                "".join(traceback.format_exception(type(error), error, error.__traceback__)[-4:])
                if with_trace
                else ""
            )
        else:
            message, trace = str(error), ""
        entry = {
            "at": datetime.now(UTC).isoformat(timespec="seconds"),
            "scope": scope,
            "message": redact(message)[:500],
        }
        if trace:
            entry["trace"] = redact(trace)[-1500:]
        with _lock:
            _errors.append(entry)
            _counts[scope] = _counts.get(scope, 0) + 1
    except Exception:  # noqa: BLE001 - diagnostics must never break the caller
        pass


def recent_errors() -> dict[str, Any]:
    with _lock:
        return {"counts": dict(_counts), "last": list(_errors)}


def clear() -> None:
    with _lock:
        _errors.clear()
        _counts.clear()


def runtime_info() -> dict[str, Any]:
    return {
        "python": sys.version.split()[0],
        "platform": platform.platform(terse=True),
        "frozen": bool(getattr(sys, "frozen", False)),
        "uptime_seconds": round(time.time() - STARTED_AT),
    }
