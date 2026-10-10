"""Real SQLite faults and concurrent connections at the history restore boundary."""

from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.diagnostics import clear, recent_errors
from app.history_backup import BackupError, export_backup, import_backup
from app.player_api import PLAYER_SERVICE
from app.player_store import PlayerStore


def _backup() -> dict[str, Any]:
    return {
        "format": "wardly-backup",
        "version": 1,
        "account_id": 123,
        "tables": {
            "players": [
                {"account_id": 77, "persona_name": "incoming"},
                {"account_id": 123, "persona_name": "new"},
            ],
            "matches": [
                {"account_id": 77, "match_id": 700, "kills": 99, "note": "incoming", "gpm": 777},
                {
                    "account_id": 123,
                    "match_id": 900,
                    "kills": 7,
                    "parsed": True,
                    "items": '["blink"]',
                },
            ],
            "meta": [
                {"key": "local_setting", "value": "incoming"},
                {"key": "imported_setting", "value": "new"},
            ],
            "cache": [
                {
                    "key": "coach:match:77:700:uk",
                    "value": '{"review":{"summary":"incoming"}}',
                    "fetched_at": 100,
                },
                {
                    "key": "coach:match:123:900:uk",
                    "value": '{"review":{"summary":"new"}}',
                    "fetched_at": 200,
                },
            ],
        },
    }


def _seed(store: PlayerStore) -> None:
    store.upsert_player(77, source="manual", persona_name="local")
    store.upsert_match(77, 700, source="gsi", fields={"kills": 5, "note": "local note"})
    store.set_meta("local_setting", "keep")
    store.cache_set("coach:match:77:700:uk", {"review": {"summary": "local"}})


def _snapshot(store: PlayerStore) -> dict[str, Any]:
    return {table: store.export_rows(table) for table in store.BACKUP_KEYS}


def _fault(store: PlayerStore, stage: str) -> None:
    if stage == "commit":
        store._conn.execute("PRAGMA foreign_keys=ON")
        store._conn.executescript("""
            CREATE TABLE backup_parent (id INTEGER PRIMARY KEY);
            CREATE TABLE backup_child (id INTEGER REFERENCES backup_parent(id) DEFERRABLE INITIALLY DEFERRED);
            CREATE TRIGGER backup_fault AFTER INSERT ON matches BEGIN
                INSERT INTO backup_child (id) VALUES (NEW.match_id);
            END;
        """)
        return
    table = (
        stage if stage in store.BACKUP_KEYS else ("players" if stage == "link_player" else "meta")
    )
    condition = {
        "link_player": "WHEN NEW.account_id = 999",
        "link_account": "WHEN NEW.key = 'primary_account_id'",
        "link_source": "WHEN NEW.key = 'primary_source'",
    }.get(stage, "")
    store._conn.execute(
        f"CREATE TRIGGER backup_fault BEFORE INSERT ON {table} {condition} BEGIN SELECT RAISE(ABORT, 'private-fault-message'); END"
    )
    store._conn.commit()


@pytest.mark.parametrize(
    "stage",
    ["players", "matches", "meta", "cache", "link_player", "link_account", "link_source", "commit"],
)
def test_http_restore_rolls_back_every_table_and_link_on_sqlite_fault(
    client: TestClient, tmp_path: Path, stage: str
) -> None:
    store = PLAYER_SERVICE.store
    _seed(store)
    before = _snapshot(store)
    data = _backup()
    if stage == "link_player":
        data["account_id"] = 999
    _fault(store, stage)
    clear()
    PLAYER_SERVICE._plans["sentinel"] = {"keep": True}
    response = client.post("/player/backup", json=data)
    assert response.status_code == 503 and response.json()["code"] == "restore_failed"
    assert _snapshot(store) == before
    assert store.primary_account_id() is None
    assert not store._conn.in_transaction
    assert PLAYER_SERVICE._plans == {"sentinel": {"keep": True}}
    assert PLAYER_SERVICE.jobs.pending() == []
    assert "private-fault-message" not in json.dumps(recent_errors())
    assert recent_errors()["counts"]["history-backup"] == 1
    store._conn.execute("DROP TRIGGER backup_fault")
    reopened = PlayerStore(store.db_path)
    try:
        assert _snapshot(reopened) == before
    finally:
        reopened.close()
    result = client.post("/player/backup", json=data)
    assert result.status_code == 200 and result.json()["linked"] is True
    assert PLAYER_SERVICE._plans == {}
    assert store.get_match(77, 700)["kills"] == 5
    assert store.get_match(77, 700)["note"] == "local note"
    assert store.get_match(77, 700)["gpm"] == 777
    again = client.post("/player/backup", json=data).json()
    assert again["linked"] is False
    assert all(counts == {"added": 0, "filled": 0} for counts in again["imported"].values())


INVALID_ROWS = [
    ("players", {"account_id": True}),
    ("players", {"account_id": -1}),
    ("players", {"account_id": 2**80}),
    ("players", {"account_id": 123, "rank_tier": 2**80}),
    ("players", {"account_id": 123, "persona_name": {"nested": 1}}),
    ("players", {"account_id": 123, "persona_name": "\ud800"}),
    ("matches", {"account_id": 123, "match_id": 2**80}),
    ("matches", {"account_id": 123, "match_id": "900"}),
    ("matches", {"account_id": 123, "match_id": 900, "kills": 1.5}),
    ("matches", {"account_id": 123, "match_id": 900, "win": 2}),
    ("matches", {"account_id": 123, "match_id": 900, "items": '["blink", 1]'}),
    ("matches", {"account_id": 123, "match_id": 900, "opendota_json": '{"players":42}'}),
    ("matches", {"account_id": 123, "match_id": 900, "analysis_json": "[]"}),
    ("matches", {"account_id": 123, "match_id": 900, "analysis_json": '{"strengths":[1]}'}),
    ("matches", {"account_id": 123, "match_id": 900, "timeline_json": "not json"}),
    ("matches", {"account_id": 123, "match_id": 900, "timeline_json": '{"samples":{},"final":[]}'}),
    ("meta", {"key": "focus:123", "value": "[]"}),
    ("meta", {"key": "rank_history:123", "value": "{}"}),
    ("meta", {"key": "setting", "value": {"nested": 1}}),
    ("cache", {"key": "coach:match:123:900:uk", "value": "not json", "fetched_at": 1}),
    ("cache", {"key": "coach:match:123:900:uk", "value": "[]", "fetched_at": 1}),
    ("cache", {"key": "coach:match:123:900:uk", "value": '{"review":42}', "fetched_at": 1}),
    ("cache", {"key": "coach:ask:123:900", "value": "[42]", "fetched_at": 1}),
    ("cache", {"key": "coach:match:123:900:uk", "value": "{}", "fetched_at": "yesterday"}),
    ("cache", {"key": "coach:match:123:900:uk", "value": "{}", "fetched_at": -1}),
    ("cache", {"key": "coach:match:123:900:uk", "value": '{"score":NaN}', "fetched_at": 1}),
    ("cache", {"key": "coach:match:123:900:uk", "value": '{"score":1e999}', "fetched_at": 1}),
    ("cache", {"key": "coach:match:123:900:uk", "value": '{"text":"\\ud800"}', "fetched_at": 1}),
]


@pytest.mark.parametrize(("table", "row"), INVALID_ROWS)
def test_invalid_row_rejects_entire_backup_before_any_sql_write(
    client: TestClient, table: str, row: dict[str, Any]
) -> None:
    store = PLAYER_SERVICE.store
    _seed(store)
    before = _snapshot(store)
    data = _backup()
    data["tables"][table].append(row)
    statements: list[str] = []
    store._conn.set_trace_callback(statements.append)
    try:
        response = client.post(
            "/player/backup", content=json.dumps(data), headers={"Content-Type": "application/json"}
        )
    finally:
        store._conn.set_trace_callback(None)
    assert response.status_code == 400 and response.json()["code"] == "not_backup"
    assert not any(
        statement.startswith(("BEGIN", "INSERT", "UPDATE", "DELETE")) for statement in statements
    )
    assert _snapshot(store) == before


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("version", True),
        ("version", 0),
        ("version", -1),
        ("version", 1.0),
        ("account_id", True),
        ("account_id", 0),
        ("account_id", 2**80),
        ("tables", []),
    ],
)
def test_invalid_header_is_rejected_without_linking(
    client: TestClient, field: str, value: Any
) -> None:
    data = _backup()
    data[field] = value
    assert client.post("/player/backup", json=data).status_code == 400
    assert PLAYER_SERVICE.store.primary_account_id() is None
    assert PLAYER_SERVICE.store.export_rows("players") == []


@pytest.mark.parametrize("rows", [None, {}, "rows", [None], [7]])
def test_malformed_known_table_is_rejected(client: TestClient, rows: Any) -> None:
    data = _backup()
    data["tables"]["cache"] = rows
    assert client.post("/player/backup", json=data).status_code == 400
    assert PLAYER_SERVICE.store.export_rows("players") == []


def test_unknown_fields_and_excluded_secrets_remain_compatible(client: TestClient) -> None:
    data = _backup()
    data["tables"]["players"][0]["future_column"] = {"ignored": True}
    data["tables"]["sqlite_master"] = [{"sql": "DROP TABLE matches"}]
    data["tables"]["meta"] += [
        {"key": key, "value": {"ignored": True}}
        for key in (
            "ai_settings",
            "opendota_api_key",
            "primary_account_id",
            "future_secret",
            "access_token",
            "password",
        )
    ]
    data["tables"]["cache"].append({"key": "opendota:items", "value": "corrupt"})
    response = client.post("/player/backup", json=data)
    assert response.status_code == 200
    assert PLAYER_SERVICE.store.primary_account_id() == 123
    assert PLAYER_SERVICE.store.get_meta("ai_settings") is None
    assert PLAYER_SERVICE.store.get_meta("future_secret") is None
    assert PLAYER_SERVICE.store.cache_get("opendota:items") is None


@pytest.mark.parametrize("fail", [False, True])
def test_other_connection_never_sees_a_partly_restored_backup(tmp_path: Path, fail: bool) -> None:
    store = PlayerStore(tmp_path / "store.sqlite3")
    reached = threading.Event()
    release = threading.Event()
    errors: list[BaseException] = []

    def pause() -> int:
        reached.set()
        assert release.wait(5)
        return 1

    def restore() -> None:
        try:
            import_backup(store, _backup())
        except BaseException as error:
            errors.append(error)

    store._conn.create_function("backup_pause", 0, pause)
    store._conn.execute(
        "CREATE TRIGGER pause_restore AFTER INSERT ON cache BEGIN SELECT backup_pause(); END"
    )
    if fail:
        _fault(store, "link_source")
    thread = threading.Thread(target=restore)
    thread.start()
    try:
        assert reached.wait(5)
        with sqlite3.connect(store.db_path) as reader:
            for table in ("players", "matches", "cache"):
                assert reader.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0
            assert (
                reader.execute(
                    "SELECT COUNT(*) FROM meta WHERE key != 'schema_version'"
                ).fetchone()[0]
                == 0
            )
    finally:
        release.set()
        thread.join(5)
    assert not thread.is_alive()
    assert bool(errors) is fail
    if fail:
        assert isinstance(errors[0], BackupError)
    assert store.count_matches(123) == (0 if fail else 1)
    assert store.primary_account_id() == (None if fail else 123)
    store.close()


def test_export_is_one_snapshot_even_with_an_external_writer(tmp_path: Path) -> None:
    store = PlayerStore(tmp_path / "store.sqlite3")
    _seed(store)
    store.set_primary(77, source="manual")
    reached = threading.Event()
    release = threading.Event()
    backups: list[dict[str, Any]] = []
    errors: list[BaseException] = []

    def authorize(
        action: int,
        table: str | None,
        column: str | None,
        database: str | None,
        trigger: str | None,
    ) -> int:
        if action == sqlite3.SQLITE_READ and table == "cache" and not reached.is_set():
            reached.set()
            assert release.wait(5)
        return sqlite3.SQLITE_OK

    def export() -> None:
        try:
            backups.append(export_backup(store, "test"))
        except BaseException as error:
            errors.append(error)

    store._conn.set_authorizer(authorize)
    thread = threading.Thread(target=export)
    thread.start()
    try:
        assert reached.wait(5)
        with sqlite3.connect(store.db_path) as writer:
            writer.execute("UPDATE players SET persona_name = 'changed'")
            writer.execute("UPDATE matches SET kills = 99")
            writer.execute("UPDATE meta SET value = '123' WHERE key = 'primary_account_id'")
            writer.execute("UPDATE cache SET value = '{}' ")
    finally:
        release.set()
        thread.join(5)
        store._conn.set_authorizer(None)
    assert not thread.is_alive() and not errors
    backup = backups[0]
    assert backup["account_id"] == 77
    assert backup["tables"]["players"][0]["persona_name"] == "local"
    assert backup["tables"]["matches"][0]["kills"] == 5
    assert json.loads(backup["tables"]["cache"][0]["value"])["review"]["summary"] == "local"
    assert store.primary_account_id() == 123
    store.close()


def test_nonfinite_timestamps_are_rejected_and_large_integers_do_not_overflow(
    tmp_path: Path,
) -> None:
    store = PlayerStore(tmp_path / "store.sqlite3")
    try:
        data = _backup()
        for value in (float("nan"), float("inf"), 10**400):
            data["tables"]["cache"][0]["fetched_at"] = value
            with pytest.raises(BackupError, match="invalid data"):
                import_backup(store, data)
            assert store.export_rows("players") == []
        data["tables"]["cache"][0]["fetched_at"] = 2**80
        assert import_backup(store, data)["linked"] is True
    finally:
        store.close()
