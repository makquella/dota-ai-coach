"""
Optional live-session recorder for real Dota GSI testing.

The recorder is off by default. When enabled, it stores raw GSI payloads,
compact normalized state summaries, shown advice cards, and session metadata
for local debugging after a live test.
"""

from __future__ import annotations

import json
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.atomic_file import write_json_atomic
from app.config import SESSION_RECORDS_DIR
from app.diagnostics import record_error


class LiveSessionRecorder:
    def __init__(self, base_dir: Path = SESSION_RECORDS_DIR) -> None:
        self.base_dir = base_dir
        self._lock = threading.Lock()
        self._active = False
        self._session_dir: Path | None = None
        self._metadata: dict[str, Any] = {}
        self._gsi_count = 0
        self._advice_count = 0
        self._failures = 0
        self._last_error: str | None = None

    def start(self) -> dict[str, Any]:
        with self._lock:
            if self._active:
                return self._status_locked()

            started_at = _now_iso()
            safe_stamp = (
                started_at.replace(":", "").replace("-", "").replace("+", "_").replace(".", "_")
            )
            self._session_dir = self.base_dir / f"live_session_{safe_stamp}_{uuid4().hex[:8]}"
            self._active = True
            self._last_error = None
            self._gsi_count = 0
            self._advice_count = 0
            self._metadata = {
                "status": "recording",
                "started_at": started_at,
                "stopped_at": None,
                "mode": "live_gsi",
                "raw_gsi_file": str(self._session_dir / "raw_gsi_states.jsonl"),
                "shown_advice_file": str(self._session_dir / "shown_advice.jsonl"),
                "gsi_count": 0,
                "advice_count": 0,
            }
            try:
                self._session_dir.mkdir(parents=True, exist_ok=True)
            except (OSError, ValueError, TypeError) as error:
                self._fail_locked("start", error)
                return self._status_locked()
            self._write_metadata_locked()
            return self._status_locked()

    def stop(self) -> dict[str, Any]:
        with self._lock:
            if not self._active:
                return self._status_locked()
            self._active = False
            self._metadata["status"] = "stopped"
            self._metadata["stopped_at"] = _now_iso()
            self._metadata["gsi_count"] = self._gsi_count
            self._metadata["advice_count"] = self._advice_count
            self._write_metadata_locked()
            return self._status_locked()

    def status(self) -> dict[str, Any]:
        with self._lock:
            return self._status_locked()

    def _status_locked(self) -> dict[str, Any]:
        return {
            "active": self._active,
            "failures": self._failures,
            "last_error": self._last_error,
            "session_dir": str(self._session_dir) if self._session_dir else None,
            "records_dir": str(self.base_dir),
            "metadata": dict(self._metadata),
            "gsi_count": self._gsi_count,
            "advice_count": self._advice_count,
        }

    def record_gsi(self, payload: dict[str, Any], state: dict[str, Any]) -> None:
        with self._lock:
            if not self._active or self._session_dir is None:
                return
            entry = {
                "timestamp": _now_iso(),
                "mode": "live_gsi",
                "hero": state.get("hero"),
                "game_time": _extra(state).get("game_time"),
                "state_summary": _state_summary(state),
                "raw_payload": payload,
            }
            self._append_jsonl_locked("raw_gsi_states.jsonl", entry)

    def record_advice(self, response: dict[str, Any], state: dict[str, Any]) -> None:
        recommendation = response.get("recommendation")
        if not isinstance(recommendation, dict):
            return
        if not response.get("new_advice"):
            return
        with self._lock:
            if not self._active or self._session_dir is None:
                return
            entry = {
                "timestamp": _now_iso(),
                "mode": "live_gsi",
                "hero": state.get("hero"),
                "game_time": _extra(state).get("game_time"),
                "decision_point": response.get("decision_point"),
                "action": recommendation.get("action"),
                "reason": recommendation.get("reason"),
                "priority": recommendation.get("priority"),
                "source": response.get("source"),
                "confidence": response.get("context_confidence"),
                "missing_signals": response.get("missing_signals", []),
                "state_summary": _state_summary(state),
            }
            self._append_jsonl_locked("shown_advice.jsonl", entry)

    def _fail_locked(self, phase: str, error: OSError | ValueError | TypeError) -> None:
        self._active = False
        self._failures += 1
        self._last_error = f"{phase}:{type(error).__name__}"
        self._metadata["status"] = "failed"
        self._metadata["stopped_at"] = _now_iso()
        record_error("live-recording-" + phase, error, with_trace=False)

    def health(self) -> dict[str, Any]:
        with self._lock:
            return {
                "active": self._active,
                "failures": self._failures,
                "last_error": self._last_error,
                "gsi_count": self._gsi_count,
                "advice_count": self._advice_count,
            }

    def _append_jsonl_locked(self, filename: str, entry: dict[str, Any]) -> None:
        if self._session_dir is None:
            return
        path = self._session_dir / filename
        try:
            with path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")
        except (OSError, ValueError, TypeError) as error:
            # Stop the optional debug recorder; future packets need no failed I/O.
            self._fail_locked("append", error)
            return
        if filename == "raw_gsi_states.jsonl":
            self._gsi_count += 1
        else:
            self._advice_count += 1
        self._metadata["gsi_count"] = self._gsi_count
        self._metadata["advice_count"] = self._advice_count
        self._write_metadata_locked()

    def _write_metadata_locked(self) -> None:
        if self._session_dir is None:
            return
        try:
            write_json_atomic(self._session_dir / "metadata.json", self._metadata, indent=2)
        except (OSError, ValueError, TypeError) as error:
            self._fail_locked("metadata", error)


def _state_summary(state: dict[str, Any]) -> dict[str, Any]:
    extra = _extra(state)
    return {
        "hero": state.get("hero"),
        "minute": state.get("minute"),
        "stage": _stage_label(state),
        "game_state": state.get("game_state"),
        "hp_percent": state.get("hp_percent"),
        "mana_percent": extra.get("mana_percent"),
        "alive": extra.get("alive"),
        "last_hits": extra.get("last_hits"),
        "gpm": extra.get("gpm"),
        "source_type": extra.get("source_type"),
        "context_confidence": extra.get("context_confidence"),
        "missing_signals": extra.get("missing_signals", []),
    }


def _stage_label(state: dict[str, Any]) -> str:
    try:
        minute = int(state.get("minute") or 0)
    except (TypeError, ValueError):
        return "unknown"
    if minute < 10:
        return "laning"
    if minute < 20:
        return "post-laning"
    return "macro"


def _extra(state: dict[str, Any]) -> dict[str, Any]:
    value = state.get("extra_context")
    return value if isinstance(value, dict) else {}


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


LIVE_SESSION_RECORDER = LiveSessionRecorder()
