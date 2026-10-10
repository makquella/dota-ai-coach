"""Automatic local copies of the history (no keys), bounded on disk.

The launcher asks once a day (`POST /player/backups/auto`); a copy is made when
the newest is a week old, or when the app version changed since the last one
(so the history before an update stays recoverable). Copies are the same
`wardly-backup` JSON as «Зберегти у файл», gzipped, in `<data>/backups/`:
at most KEEP copies and BUDGET_BYTES together, the oldest go first, the newest
always stays. A small sidecar per copy keeps its counts for the list, so
listing never unpacks a copy. Restoring goes through history_backup: a preview
(the merge run and rolled back) first, then the atomic merge.

Before the store's schema changes, PlayerService snapshots the SQLite file
itself with SQLite's backup API (`pre_migration_snapshot`), for recovery by
hand; those are kept two at a time.
"""

from __future__ import annotations

import gzip
import json
import os
import re
import sqlite3
import tempfile
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.history_backup import BackupError

KEEP = 4
BUDGET_BYTES = 200 * 1024 * 1024
EVERY_SECONDS = 7 * 24 * 3600
KEEP_SNAPSHOTS = 2
KINDS = ("weekly", "update", "manual")
NAME = re.compile(r"^wardly-backup-(\d{8}T\d{6}Z)-(weekly|update|manual)\.json\.gz$")
SNAPSHOT = re.compile(r"^coach-pre-schema-(\d+)-(\d{8}T\d{6}Z)\.sqlite3$")


class AutoBackups:
    def __init__(self, directory: Path, *, clock: Callable[[], float] = time.time) -> None:
        self.directory = Path(directory)
        self._clock = clock

    # --- copies -------------------------------------------------------------------

    def items(self) -> list[dict[str, Any]]:
        """Newest first: id, kind, created_at, size and the sidecar's counts."""
        if not self.directory.is_dir():
            return []
        items = []
        for path in self.directory.iterdir():
            match = NAME.match(path.name)
            if not match or not path.is_file():
                continue
            info = self._sidecar(path)
            items.append(
                {
                    "id": path.name,
                    "kind": match.group(2),
                    "created_at": _iso(match.group(1)),
                    "size": path.stat().st_size,
                    "matches": info.get("matches"),
                    "app_version": info.get("app_version"),
                }
            )
        return sorted(items, key=lambda item: item["id"].split("-")[2], reverse=True)

    def newest_age(self) -> float | None:
        """Seconds since the newest copy, None without one."""
        items = self.items()
        if not items:
            return None
        made = datetime.fromisoformat(items[0]["created_at"]).timestamp()
        return max(0.0, self._clock() - made)

    def write(self, data: dict[str, Any], kind: str) -> dict[str, Any]:
        """One copy, written atomically, then the rotation."""
        if kind not in KINDS:
            raise ValueError(kind)
        self.directory.mkdir(parents=True, exist_ok=True)
        stamp = datetime.fromtimestamp(self._clock(), UTC).strftime("%Y%m%dT%H%M%SZ")
        path = self.directory / f"wardly-backup-{stamp}-{kind}.json.gz"
        payload = gzip.compress(json.dumps(data, ensure_ascii=False).encode("utf-8"), 6)
        _atomic_write(path, payload)
        raw_counts = data.get("counts")
        counts = raw_counts if isinstance(raw_counts, dict) else {}
        _atomic_write(
            _sidecar_path(path),
            json.dumps(
                {"matches": counts.get("matches"), "app_version": data.get("app_version")}
            ).encode("utf-8"),
        )
        self.rotate()
        return next(item for item in self.items() if item["id"] == path.name)

    def read(self, backup_id: str) -> dict[str, Any]:
        """The copy's backup JSON; KeyError for an unknown or malformed id."""
        if not NAME.match(str(backup_id)):
            raise KeyError(backup_id)
        path = self.directory / str(backup_id)
        if not path.is_file():
            raise KeyError(backup_id)
        try:
            with gzip.open(path, "rb") as stream:
                data = json.loads(stream.read().decode("utf-8"))
        except (OSError, EOFError, ValueError) as error:
            raise BackupError("not_backup", "The copy is damaged.") from error
        if not isinstance(data, dict):
            raise BackupError("not_backup", "The copy is damaged.")
        return data

    def rotate(self) -> list[str]:
        """Drop the oldest beyond KEEP copies or BUDGET_BYTES; the newest stays."""
        items = self.items()
        removed = []
        total = sum(item["size"] for item in items)
        for index, item in reversed(list(enumerate(items))):
            if index == 0:
                break
            if index < KEEP and total <= BUDGET_BYTES:
                continue
            path = self.directory / item["id"]
            path.unlink(missing_ok=True)
            _sidecar_path(path).unlink(missing_ok=True)
            total -= item["size"]
            removed.append(item["id"])
        return removed

    # --- schema snapshots ---------------------------------------------------------

    def pre_migration_snapshot(self, db_path: Path, target_version: int) -> Path | None:
        """A consistent copy of an existing store whose schema is older than
        `target_version`, made before the store is opened; None when not needed."""
        version = _schema_version(db_path)
        if version is None or version >= target_version:
            return None
        self.directory.mkdir(parents=True, exist_ok=True)
        stamp = datetime.fromtimestamp(self._clock(), UTC).strftime("%Y%m%dT%H%M%SZ")
        target = self.directory / f"coach-pre-schema-{version}-{stamp}.sqlite3"
        source = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        try:
            copy = sqlite3.connect(str(target))
            try:
                source.backup(copy)
            finally:
                copy.close()
        finally:
            source.close()
        snapshots = sorted(
            (path for path in self.directory.iterdir() if SNAPSHOT.match(path.name)),
            key=lambda path: path.name.rsplit("-", 1)[1],
            reverse=True,
        )
        for old in snapshots[KEEP_SNAPSHOTS:]:
            old.unlink(missing_ok=True)
        return target

    @staticmethod
    def _sidecar(path: Path) -> dict[str, Any]:
        try:
            value = json.loads(_sidecar_path(path).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        return value if isinstance(value, dict) else {}


def _sidecar_path(path: Path) -> Path:
    return path.with_name(path.name.removesuffix(".json.gz") + ".info.json")


def _iso(stamp: str) -> str:
    return datetime.strptime(stamp, "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC).isoformat()


def _atomic_write(path: Path, payload: bytes) -> None:
    descriptor, temp = tempfile.mkstemp(dir=path.parent, prefix=".tmp-", suffix=".part")
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    except BaseException:
        Path(temp).unlink(missing_ok=True)
        raise


def _schema_version(db_path: Path) -> int | None:
    if not Path(db_path).is_file():
        return None
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        try:
            row = conn.execute("SELECT value FROM meta WHERE key = 'schema_version'").fetchone()
        finally:
            conn.close()
    except sqlite3.Error:
        return None
    try:
        return int(row[0]) if row else 0
    except (TypeError, ValueError):
        return 0
