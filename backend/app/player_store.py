"""
player_store.py - local SQLite store for the linked player and their matches.

One file, PLAYER_DATA_DIR/coach.sqlite3 (under %APPDATA%\\DotaAICoach in the
installed app). It keeps:

- players: accounts seen by the app (linked by hand or detected from GSI);
- meta: which account is the primary one ("my account");
- matches: one row per (account, match) with summary columns for the match
  table, plus JSON blobs: the trimmed OpenDota match, the GSI timeline the
  app recorded live, and the last post-match analysis.

Nothing here talks to the network; see opendota.py and player_service.py.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1

# Summary columns shown in the match table (all optional).
MATCH_COLUMNS = (
    "start_time",
    "duration",
    "hero_id",
    "hero",
    "is_radiant",
    "win",
    "kills",
    "deaths",
    "assists",
    "gpm",
    "xpm",
    "last_hits",
    "denies",
    "lh_10",
    "net_worth",
    "hero_damage",
    "lane_role",
    "game_mode",
    "lobby_type",
    "parsed",
    "score",
)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT
);
CREATE TABLE IF NOT EXISTS players (
    account_id INTEGER PRIMARY KEY,
    steam_id64 TEXT,
    persona_name TEXT,
    avatar_url TEXT,
    rank_tier INTEGER,
    source TEXT,
    first_seen_at TEXT,
    updated_at TEXT
);
CREATE TABLE IF NOT EXISTS matches (
    account_id INTEGER NOT NULL,
    match_id INTEGER NOT NULL,
    start_time INTEGER,
    duration INTEGER,
    hero_id INTEGER,
    hero TEXT,
    is_radiant INTEGER,
    win INTEGER,
    kills INTEGER,
    deaths INTEGER,
    assists INTEGER,
    gpm INTEGER,
    xpm INTEGER,
    last_hits INTEGER,
    denies INTEGER,
    lh_10 INTEGER,
    net_worth INTEGER,
    hero_damage INTEGER,
    lane_role INTEGER,
    game_mode INTEGER,
    lobby_type INTEGER,
    parsed INTEGER DEFAULT 0,
    score INTEGER,
    sources TEXT DEFAULT '',
    parse_status TEXT DEFAULT '',
    opendota_json TEXT,
    timeline_json TEXT,
    analysis_json TEXT,
    updated_at TEXT,
    PRIMARY KEY (account_id, match_id)
);
CREATE INDEX IF NOT EXISTS matches_by_time ON matches (account_id, start_time DESC);
CREATE TABLE IF NOT EXISTS cache (
    key TEXT PRIMARY KEY,
    value TEXT,
    fetched_at REAL
);
"""


def _now() -> str:
    return datetime.now(UTC).isoformat()


class PlayerStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        with self._lock:
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.executescript(_SCHEMA)
            self._set_meta("schema_version", str(SCHEMA_VERSION))
            self._conn.commit()

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    # --- meta / primary account ---------------------------------------------

    def _get_meta(self, key: str) -> str | None:
        row = self._conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
        return None if row is None else row["value"]

    def _set_meta(self, key: str, value: str | None) -> None:
        if value is None:
            self._conn.execute("DELETE FROM meta WHERE key = ?", (key,))
        else:
            self._conn.execute(
                "INSERT INTO meta (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, value),
            )

    def primary_account_id(self) -> int | None:
        with self._lock:
            value = self._get_meta("primary_account_id")
        return int(value) if value else None

    def set_primary(self, account_id: int, *, source: str) -> None:
        with self._lock:
            self._touch_player(account_id, source=source)
            self._set_meta("primary_account_id", str(int(account_id)))
            self._set_meta("primary_source", source)
            self._conn.commit()

    def primary_source(self) -> str | None:
        with self._lock:
            return self._get_meta("primary_source")

    def clear_primary(self) -> None:
        with self._lock:
            self._set_meta("primary_account_id", None)
            self._set_meta("primary_source", None)
            self._conn.commit()

    def get_meta(self, key: str) -> str | None:
        with self._lock:
            return self._get_meta(key)

    def set_meta(self, key: str, value: str | None) -> None:
        with self._lock:
            self._set_meta(key, value)
            self._conn.commit()

    # --- cache (OpenDota meta data: items, hero builds, bracket win rates) -----

    def cache_get(self, key: str, *, max_age: float | None = None) -> Any:
        """Cached JSON value, or None when missing or older than max_age seconds."""
        with self._lock:
            row = self._conn.execute(
                "SELECT value, fetched_at FROM cache WHERE key = ?", (key,)
            ).fetchone()
        if row is None:
            return None
        if max_age is not None and time.time() - float(row["fetched_at"] or 0) > max_age:
            return None
        return json.loads(row["value"])

    def cache_set(self, key: str, value: Any) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO cache (key, value, fetched_at) VALUES (?, ?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value, "
                "fetched_at = excluded.fetched_at",
                (key, json.dumps(value, ensure_ascii=False), time.time()),
            )
            self._conn.commit()

    # --- players ------------------------------------------------------------

    def _touch_player(self, account_id: int, *, source: str) -> None:
        now = _now()
        self._conn.execute(
            "INSERT INTO players (account_id, source, first_seen_at, updated_at) "
            "VALUES (?, ?, ?, ?) ON CONFLICT(account_id) DO NOTHING",
            (int(account_id), source, now, now),
        )

    def upsert_player(self, account_id: int, *, source: str, **fields: Any) -> None:
        allowed = {"steam_id64", "persona_name", "avatar_url", "rank_tier"}
        updates = {key: value for key, value in fields.items() if key in allowed and value}
        with self._lock:
            self._touch_player(account_id, source=source)
            if updates:
                assignments = ", ".join(f"{key} = ?" for key in updates)
                self._conn.execute(
                    f"UPDATE players SET {assignments}, updated_at = ? WHERE account_id = ?",
                    (*updates.values(), _now(), int(account_id)),
                )
            self._conn.commit()

    def get_player(self, account_id: int) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM players WHERE account_id = ?", (int(account_id),)
            ).fetchone()
        return dict(row) if row else None

    # --- matches ------------------------------------------------------------

    def upsert_match(
        self,
        account_id: int,
        match_id: int,
        *,
        source: str | None,
        fields: dict[str, Any] | None = None,
        opendota: dict[str, Any] | None = None,
        timeline: dict[str, Any] | None = None,
        analysis: dict[str, Any] | None = None,
        parse_status: str | None = None,
    ) -> None:
        """Insert or merge one match. Missing values never erase stored ones."""
        values = {
            key: value
            for key, value in (fields or {}).items()
            if key in MATCH_COLUMNS and value is not None
        }
        with self._lock:
            row = self._conn.execute(
                "SELECT sources FROM matches WHERE account_id = ? AND match_id = ?",
                (int(account_id), int(match_id)),
            ).fetchone()
            sources = set(filter(None, (row["sources"] if row else "").split(",")))
            if source:
                sources.add(source)
            if row is None:
                self._conn.execute(
                    "INSERT INTO matches (account_id, match_id, sources, updated_at) "
                    "VALUES (?, ?, ?, ?)",
                    (int(account_id), int(match_id), "", _now()),
                )
            blobs: dict[str, Any] = {"sources": ",".join(sorted(sources)), "updated_at": _now()}
            if opendota is not None:
                blobs["opendota_json"] = json.dumps(opendota, ensure_ascii=False)
            if timeline is not None:
                blobs["timeline_json"] = json.dumps(timeline, ensure_ascii=False)
            if analysis is not None:
                blobs["analysis_json"] = json.dumps(analysis, ensure_ascii=False)
            if parse_status is not None:
                blobs["parse_status"] = parse_status
            updates = {**values, **blobs}
            assignments = ", ".join(f"{key} = ?" for key in updates)
            self._conn.execute(
                f"UPDATE matches SET {assignments} WHERE account_id = ? AND match_id = ?",
                (*updates.values(), int(account_id), int(match_id)),
            )
            self._conn.commit()

    @staticmethod
    def _filter(
        account_id: int, hero_id: int | None, win: bool | None
    ) -> tuple[str, tuple[Any, ...]]:
        """WHERE clause for the match table filters (hero, result)."""
        where, params = ["account_id = ?"], [int(account_id)]
        if hero_id is not None:
            where.append("hero_id = ?")
            params.append(int(hero_id))
        if win is not None:
            where.append("win = ?")
            params.append(1 if win else 0)
        return " AND ".join(where), tuple(params)

    def list_matches(
        self,
        account_id: int,
        *,
        limit: int = 50,
        offset: int = 0,
        hero_id: int | None = None,
        win: bool | None = None,
    ) -> list[dict[str, Any]]:
        columns = ", ".join(("match_id", *MATCH_COLUMNS, "sources", "parse_status"))
        where, params = self._filter(account_id, hero_id, win)
        with self._lock:
            rows = self._conn.execute(
                f"SELECT {columns}, analysis_json IS NOT NULL AS has_analysis, "
                f"timeline_json IS NOT NULL AS has_timeline FROM matches WHERE {where} "
                "ORDER BY COALESCE(start_time, 0) DESC, match_id DESC LIMIT ? OFFSET ?",
                (*params, int(limit), int(offset)),
            ).fetchall()
        return [_summary_row(row) for row in rows]

    def count_matches(
        self, account_id: int, *, hero_id: int | None = None, win: bool | None = None
    ) -> int:
        where, params = self._filter(account_id, hero_id, win)
        with self._lock:
            row = self._conn.execute(
                f"SELECT COUNT(*) AS n FROM matches WHERE {where}", params
            ).fetchone()
        return int(row["n"]) if row else 0

    def match_stats(
        self, account_id: int, *, hero_id: int | None = None, win: bool | None = None
    ) -> dict[str, Any]:
        """Games, wins (of those with a known result) and average score of a filter."""
        where, params = self._filter(account_id, hero_id, win)
        with self._lock:
            row = self._conn.execute(
                "SELECT COUNT(*) AS games, SUM(win = 1) AS wins, "
                "SUM(win IS NOT NULL) AS decided, AVG(score) AS avg_score "
                f"FROM matches WHERE {where}",
                params,
            ).fetchone()
        decided = int(row["decided"] or 0)
        return {
            "games": int(row["games"] or 0),
            "wins": int(row["wins"] or 0),
            "winrate": round(100 * int(row["wins"] or 0) / decided) if decided else None,
            "avg_score": round(row["avg_score"]) if row["avg_score"] is not None else None,
        }

    def hero_counts(self, account_id: int) -> list[dict[str, Any]]:
        """Heroes of the stored matches, most played first (filter choices)."""
        with self._lock:
            rows = self._conn.execute(
                "SELECT hero_id, MAX(hero) AS hero, COUNT(*) AS games FROM matches "
                "WHERE account_id = ? AND hero_id IS NOT NULL GROUP BY hero_id "
                "ORDER BY games DESC, hero",
                (int(account_id),),
            ).fetchall()
        return [
            {"hero_id": int(row["hero_id"]), "hero": row["hero"], "games": int(row["games"])}
            for row in rows
        ]

    def source_counts(self, account_id: int) -> dict[str, int]:
        """How many matches per parse status (problem report)."""
        with self._lock:
            rows = self._conn.execute(
                "SELECT COALESCE(NULLIF(parse_status, ''), 'none') AS status, COUNT(*) AS n "
                "FROM matches WHERE account_id = ? GROUP BY status",
                (int(account_id),),
            ).fetchall()
        return {str(row["status"]): int(row["n"]) for row in rows}

    def delete_matches(self, account_id: int, match_ids: list[int]) -> int:
        if not match_ids:
            return 0
        marks = ", ".join("?" for _ in match_ids)
        with self._lock:
            cursor = self._conn.execute(
                f"DELETE FROM matches WHERE account_id = ? AND match_id IN ({marks})",
                (int(account_id), *(int(m) for m in match_ids)),
            )
            self._conn.commit()
        return int(cursor.rowcount or 0)

    def mode_rows(self, account_id: int) -> list[dict[str, Any]]:
        """match_id, lobby_type and game_mode of every stored match."""
        with self._lock:
            rows = self._conn.execute(
                "SELECT match_id, lobby_type, game_mode FROM matches WHERE account_id = ?",
                (int(account_id),),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_match(self, account_id: int, match_id: int) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM matches WHERE account_id = ? AND match_id = ?",
                (int(account_id), int(match_id)),
            ).fetchone()
        if row is None:
            return None
        record = dict(row)
        for column, key in (
            ("opendota_json", "opendota"),
            ("timeline_json", "timeline"),
            ("analysis_json", "analysis"),
        ):
            raw = record.pop(column, None)
            record[key] = json.loads(raw) if raw else None
        record["sources"] = [item for item in (record.get("sources") or "").split(",") if item]
        return record

    def matches_for_career(
        self, account_id: int, *, limit: int = 50, hero_id: int | None = None
    ) -> list[dict[str, Any]]:
        """Newest first, summary columns plus the stored analysis (for trends)."""
        columns = ", ".join(("match_id", *MATCH_COLUMNS, "sources"))
        where, params = self._filter(account_id, hero_id, None)
        with self._lock:
            rows = self._conn.execute(
                f"SELECT {columns}, analysis_json FROM matches WHERE {where} "
                "ORDER BY COALESCE(start_time, 0) DESC, match_id DESC LIMIT ?",
                (*params, int(limit)),
            ).fetchall()
        result = []
        for row in rows:
            record = _summary_row(row)
            raw = row["analysis_json"]
            record["analysis"] = json.loads(raw) if raw else None
            result.append(record)
        return result


def _summary_row(row: sqlite3.Row) -> dict[str, Any]:
    # sqlite3.Row iterates over values, so .keys() is needed here.
    record = {key: row[key] for key in row.keys() if key != "analysis_json"}  # noqa: SIM118
    for flag in ("is_radiant", "win", "parsed", "has_analysis", "has_timeline"):
        if flag in record and record[flag] is not None:
            record[flag] = bool(record[flag])
    record["sources"] = [item for item in (record.get("sources") or "").split(",") if item]
    return record
