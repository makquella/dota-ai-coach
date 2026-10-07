"""
history_backup.py - the player's history in one file, and back.

The export holds the store's tables (player_store.py): players, every match
(summary columns, the OpenDota match, the live GSI timeline, the review), the
settings kept in `meta` (focus, friend, ...) and the AI coach's reviews and
answers from `cache`. Never in it: the OpenDota and AI keys (and any other
meta value that looks like a secret), the OpenDota meta cache (fetched again)
and which account is linked on this computer.

The import merges: rows that are missing are added, stored rows only get the
values they lack, nothing is deleted or overwritten. When no account is linked
yet, the backup's account becomes the linked one.

The launcher gzips the JSON into `Wardly-backup-<date>.json.gz`.
"""

from __future__ import annotations

import math
import re
import sqlite3
from datetime import UTC, datetime
from typing import Any

from app.diagnostics import record_error
from app.player_store import MATCH_COLUMNS, PlayerStore
from app.storage_json import cache_value_valid, load_json

FORMAT = "wardly-backup"
VERSION = 1
# Settings of this computer or secrets: never exported, never imported.
LOCAL_META = {
    "schema_version",
    "primary_account_id",
    "primary_source",
    "opendota_api_key",
    "ai_settings",
}
SECRET = re.compile(r"key|token|secret|password", re.IGNORECASE)
# The AI coach's reviews and answers (the model's quota was spent on them).
CACHE_PREFIXES = ("coach:",)
SQLITE_MAX = 2**63 - 1
MATCH_TEXT = {
    "hero",
    "items",
    "note",
    "sources",
    "parse_status",
    "opendota_json",
    "timeline_json",
    "analysis_json",
    "updated_at",
}
MATCH_INTEGERS = (set(MATCH_COLUMNS) - MATCH_TEXT) | {"account_id", "match_id"}
PLAYER_TEXT = {"steam_id64", "persona_name", "avatar_url", "source", "first_seen_at", "updated_at"}
JSON_OBJECTS = {"opendota_json", "timeline_json", "analysis_json"}
# Minimum container shapes consumed by history/facts; optional fields remain optional.
JSON_CONTAINERS: dict[str, dict[str, type]] = {
    "opendota_json": {"players": list},
    "timeline_json": {
        "samples": list,
        "deaths": list,
        "advice": list,
        "items": list,
        "buybacks": list,
        "final": dict,
        "scores": dict,
    },
    "analysis_json": {"headline": dict, "strengths": list, "improvements": list},
}
META_JSON = {
    "focus": dict,
    "friend": dict,
    "cosmetics": dict,
    "rank_history": list,
    "mmr": list,
    "skipped_modes": dict,
}


class BackupError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _meta_allowed(key: Any) -> bool:
    return isinstance(key, str) and key not in LOCAL_META and not SECRET.search(key)


def _cache_allowed(key: Any) -> bool:
    return isinstance(key, str) and key.startswith(CACHE_PREFIXES)


def export_backup(store: PlayerStore, app_version: str) -> dict[str, Any]:
    tables, account = store.backup_snapshot()
    return {
        "format": FORMAT,
        "version": VERSION,
        "created_at": datetime.now(UTC).isoformat(),
        "app_version": app_version,
        "account_id": account,
        "counts": {"matches": len(tables["matches"])},
        "tables": {
            "players": tables["players"],
            "matches": tables["matches"],
            "meta": [row for row in tables["meta"] if _meta_allowed(row.get("key"))],
            "cache": [row for row in tables["cache"] if _cache_allowed(row.get("key"))],
        },
    }


def _invalid() -> BackupError:
    # Never include a supplied key/value in an HTTP error or diagnostic.
    return BackupError("not_backup", "The history backup contains invalid data.")


def _integer(value: Any, *, positive: bool = False) -> bool:
    return type(value) is int and (1 if positive else -(2**63)) <= value <= SQLITE_MAX


def _text(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        value.encode("utf-8")
    except UnicodeError:
        return False
    return True


def _json(raw: Any, kind: type) -> Any:
    if not isinstance(raw, str):
        raise _invalid()
    try:
        value = load_json(raw)
    except (ValueError, TypeError, OverflowError, RecursionError):
        raise _invalid() from None
    if not isinstance(value, kind):
        raise _invalid()
    return value


def _validate_row(table: str, raw: dict[str, Any]) -> dict[str, Any]:
    if table in {"players", "matches"}:
        integers = MATCH_INTEGERS if table == "matches" else {"account_id", "rank_tier"}
        text = MATCH_TEXT if table == "matches" else PLAYER_TEXT
        row = {key: value for key, value in raw.items() if key in integers | text}
        for key in PlayerStore.BACKUP_KEYS[table]:
            if not _integer(row.get(key), positive=True):
                raise _invalid()
        for key, value in row.items():
            if value is None:
                continue
            if key in {"win", "is_radiant", "parsed"}:
                if not isinstance(value, (int, bool)) or value not in (0, 1):
                    raise _invalid()
            elif key in integers:
                if not _integer(value):
                    raise _invalid()
            elif not _text(value):
                raise _invalid()
            if key in JSON_OBJECTS:
                blob = _json(value, dict)
                for field, kind in JSON_CONTAINERS[key].items():
                    part = blob.get(field)
                    if part is not None and not isinstance(part, kind):
                        raise _invalid()
                    if isinstance(part, list) and any(not isinstance(item, dict) for item in part):
                        raise _invalid()
            elif key == "items":
                if any(not isinstance(item, str) for item in _json(value, list)):
                    raise _invalid()
        return row
    meta_key = raw.get("key")
    if not _text(meta_key) or not meta_key:
        raise _invalid()
    value = raw.get("value")
    if table == "meta":
        if value is not None and not _text(value):
            raise _invalid()
        meta_kind = META_JSON.get(meta_key.split(":", 1)[0])
        if value is not None and meta_kind is not None:
            _json(value, meta_kind)
        return {"key": meta_key, "value": value}
    try:
        decoded = load_json(value) if isinstance(value, str) else None
    except (ValueError, TypeError, OverflowError, RecursionError):
        raise _invalid() from None
    fetched_at = raw.get("fetched_at")
    if (
        not isinstance(value, str)
        or not cache_value_valid(meta_key, decoded)
        or isinstance(fetched_at, bool)
        or not isinstance(fetched_at, (int, float))
    ):
        raise _invalid()
    try:
        fetched_at = float(fetched_at)
        valid_time = math.isfinite(fetched_at) and fetched_at >= 0
    except OverflowError:
        valid_time = False
    if not valid_time:
        raise _invalid()
    return {"key": meta_key, "value": value, "fetched_at": fetched_at}


def import_backup(store: PlayerStore, data: Any) -> dict[str, Any]:
    """Validate all accepted rows before atomically merging the history."""
    if not isinstance(data, dict) or data.get("format") != FORMAT:
        raise BackupError("not_backup", "This file is not a Wardly history backup.")
    version = data.get("version")
    if type(version) is not int or version < 1:
        raise _invalid()
    if version > VERSION:
        raise BackupError("newer_version", "The backup was made by a newer version of Wardly.")
    tables = data.get("tables")
    if not isinstance(tables, dict):
        raise BackupError("not_backup", "The backup has no data.")

    account = data.get("account_id")
    if account is not None and not _integer(account, positive=True):
        raise _invalid()
    validated = {}
    for table in PlayerStore.BACKUP_KEYS:
        rows = tables.get(table, [])
        if not isinstance(rows, list):
            raise _invalid()
        accepted = []
        for row in rows:
            if not isinstance(row, dict):
                raise _invalid()
            if table in {"meta", "cache"}:
                key = row.get("key")
                if not isinstance(key, str) or not key:
                    raise _invalid()
                if (table == "meta" and not _meta_allowed(key)) or (
                    table == "cache" and not _cache_allowed(key)
                ):
                    continue
            accepted.append(_validate_row(table, row))
        validated[table] = accepted
    try:
        return store.merge_backup(validated, account)
    except sqlite3.Error as error:
        record_error(
            "history-backup", f"Restore rolled back: {type(error).__name__}", with_trace=False
        )
        raise BackupError(
            "restore_failed", "Could not restore the history; no changes were saved."
        ) from None
