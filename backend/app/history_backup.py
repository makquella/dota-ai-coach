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

import re
from datetime import UTC, datetime
from typing import Any

from app.player_store import PlayerStore

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


class BackupError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _meta_allowed(key: Any) -> bool:
    return isinstance(key, str) and key not in LOCAL_META and not SECRET.search(key)


def _cache_allowed(key: Any) -> bool:
    return isinstance(key, str) and key.startswith(CACHE_PREFIXES)


def export_backup(store: PlayerStore, app_version: str) -> dict[str, Any]:
    matches = store.export_rows("matches")
    return {
        "format": FORMAT,
        "version": VERSION,
        "created_at": datetime.now(UTC).isoformat(),
        "app_version": app_version,
        "account_id": store.primary_account_id(),
        "counts": {"matches": len(matches)},
        "tables": {
            "players": store.export_rows("players"),
            "matches": matches,
            "meta": [row for row in store.export_rows("meta") if _meta_allowed(row.get("key"))],
            "cache": [row for row in store.export_rows("cache") if _cache_allowed(row.get("key"))],
        },
    }


def import_backup(store: PlayerStore, data: Any) -> dict[str, Any]:
    """Merge a backup into the store. Raises BackupError for a file that is not one."""
    if not isinstance(data, dict) or data.get("format") != FORMAT:
        raise BackupError("not_backup", "This file is not a Wardly history backup.")
    if not isinstance(data.get("version"), int) or data["version"] > VERSION:
        raise BackupError("newer_version", "The backup was made by a newer version of Wardly.")
    tables = data.get("tables")
    if not isinstance(tables, dict):
        raise BackupError("not_backup", "The backup has no data.")

    def rows(name: str) -> list[dict[str, Any]]:
        value = tables.get(name)
        return [row for row in value if isinstance(row, dict)] if isinstance(value, list) else []

    result = {
        "players": store.import_rows("players", rows("players")),
        "matches": store.import_rows("matches", rows("matches")),
        "meta": store.import_rows(
            "meta", [row for row in rows("meta") if _meta_allowed(row.get("key"))]
        ),
        "cache": store.import_rows(
            "cache", [row for row in rows("cache") if _cache_allowed(row.get("key"))]
        ),
    }
    account = data.get("account_id")
    linked = False
    if store.primary_account_id() is None and isinstance(account, int) and account > 0:
        store.set_primary(account, source="backup")
        linked = True
    return {"imported": result, "linked": linked, "account_id": store.primary_account_id()}
