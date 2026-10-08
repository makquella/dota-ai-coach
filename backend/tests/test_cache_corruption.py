"""Corrupt persisted cache values are diagnosed, removed and fetched again."""

from __future__ import annotations

import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from match_fixtures import MATCH_ID, ME, FakeOpenDota, opendota_match, recent_matches

from app.coach_review import COACH_VERSION
from app.diagnostics import clear, recent_errors
from app.player_api import PLAYER_SERVICE
from app.player_store import PlayerStore


def _raw(store: PlayerStore, key: str, value: Any, fetched_at: Any = None) -> None:
    store._conn.execute(
        "INSERT OR REPLACE INTO cache(key, value, fetched_at) VALUES (?, ?, ?)",
        (key, value, time.time() if fetched_at is None else fetched_at),
    )
    store._conn.commit()


@pytest.mark.parametrize(
    ("key", "value", "fetched_at"),
    [
        ("coach:private-key", "private-payload", 1),
        ("coach:private-key", None, 1),
        ("coach:private-key", "[]", 1),
        ("coach:private-key", '{"review":42}', 1),
        ("coach:private-key", '{"provider":[]}', 1),
        ("coach:private-key", '{"score":NaN}', 1),
        ("coach:private-key", '{"score":1e999}', 1),
        ("coach:private-key", '{"text":"\\ud800"}', 1),
        ("coach:ask:private-key", "[1]", 1),
        ("opendota:items", "[]", 1),
        ("opendota:hero_stats", "{}", 1),
        ("friend:matches:private-key", "[]", 1),
        ("friend:matches:private-key", '{"profile":[]}', 1),
        ("coach:private-key", "{}", "invalid-time"),
        ("coach:private-key", "{}", float("inf")),
        ("coach:private-key", "{}", -1),
    ],
)
def test_corrupt_cache_is_a_miss_without_private_data_in_diagnostics(
    tmp_path: Path, key: str, value: Any, fetched_at: Any
) -> None:
    store = PlayerStore(tmp_path / "store.sqlite3")
    try:
        store.cache_set("untouched", {"keep": True})
        _raw(store, key, value, fetched_at)
        clear()
        # Corruption is removed even when the timestamp would make the row expired.
        assert store.cache_get(key, max_age=1) is None
        assert store.cache_get(key) is None
        assert [row["key"] for row in store.export_rows("cache")] == ["untouched"]
        assert store.cache_get("untouched") == {"keep": True}
        errors = recent_errors()
        assert errors["counts"]["player-cache"] == 1
        assert "private-key" not in json.dumps(errors)
        assert "private-payload" not in json.dumps(errors)
        assert not any("trace" in entry for entry in errors["last"])
    finally:
        store.close()


def test_failed_cache_cleanup_remains_a_miss_and_recovers_after_fault(tmp_path: Path) -> None:
    store = PlayerStore(tmp_path / "store.sqlite3")
    try:
        _raw(store, "coach:bad", "private-payload")
        store._conn.execute(
            "CREATE TRIGGER cache_fault BEFORE DELETE ON cache BEGIN SELECT RAISE(ABORT, 'private-delete-fault'); END"
        )
        clear()
        assert store.cache_get("coach:bad") is None
        assert len(store.export_rows("cache")) == 1
        assert not store._conn.in_transaction
        assert recent_errors()["counts"]["player-cache"] == 2
        assert "private-delete-fault" not in json.dumps(recent_errors())
        store._conn.execute("DROP TRIGGER cache_fault")
        assert store.cache_get("coach:bad") is None
        assert store.export_rows("cache") == []
        store.cache_set("coach:bad", {"review": {"summary": "new"}})
        assert store.cache_get("coach:bad")["review"]["summary"] == "new"
    finally:
        store.close()


def test_json_null_remains_a_valid_explicit_cache_miss(tmp_path: Path) -> None:
    store = PlayerStore(tmp_path / "store.sqlite3")
    try:
        clear()
        for key in ("coach:match:123:900:ru", "friend:matches:123", "opendota:items"):
            store.cache_set(key, None)
            assert store.cache_get(key) is None
        assert len(store.export_rows("cache")) == 3
        assert recent_errors()["counts"] == {}
    finally:
        store.close()


def test_cleanup_keeps_a_valid_value_refreshed_by_another_connection(tmp_path: Path) -> None:
    store = PlayerStore(tmp_path / "store.sqlite3")
    _raw(store, "coach:entry", "corrupt")
    reached = threading.Event()
    release = threading.Event()
    results: list[Any] = []
    errors: list[BaseException] = []

    def authorize(
        action: int,
        table: str | None,
        column: str | None,
        database: str | None,
        trigger: str | None,
    ) -> int:
        if action == sqlite3.SQLITE_DELETE and table == "cache":
            reached.set()
            assert release.wait(5)
        return sqlite3.SQLITE_OK

    def read() -> None:
        try:
            results.append(store.cache_get("coach:entry"))
        except BaseException as error:
            errors.append(error)

    store._conn.set_authorizer(authorize)
    thread = threading.Thread(target=read)
    thread.start()
    try:
        assert reached.wait(5)
        with sqlite3.connect(store.db_path) as writer:
            writer.execute(
                "UPDATE cache SET value = ?, fetched_at = ? WHERE key = ?",
                ('{"review":{"summary":"fresh"}}', time.time(), "coach:entry"),
            )
    finally:
        release.set()
        thread.join(5)
        store._conn.set_authorizer(None)
    assert not thread.is_alive() and not errors
    assert results == [None]
    assert store.cache_get("coach:entry")["review"]["summary"] == "fresh"
    store.close()


def test_match_http_survives_corrupt_constants_reviews_and_questions(
    client: TestClient, tmp_path: Path
) -> None:
    fake = FakeOpenDota(matches={MATCH_ID: opendota_match()}, recent=recent_matches(1))
    PLAYER_SERVICE.configure(tmp_path / "history", client=fake, auto_start=False)
    assert client.post("/player/link", json={"steam": str(ME)}).status_code == 200
    PLAYER_SERVICE.jobs.run_pending(until=float("inf"))
    store = PLAYER_SERVICE.store
    keys = ["opendota:items", f"coach:match:{ME}:{MATCH_ID}:ru", f"coach:ask:{ME}:{MATCH_ID}"]
    for key in keys:
        _raw(store, key, "private-payload")
    clear()
    response = client.get(f"/player/matches/{MATCH_ID}?lang=ru")
    assert response.status_code == 200
    assert response.json()["analysis"]["headline"]["hero"]
    assert response.json()["coach"]["state"] == "off"
    assert response.json()["questions"] == []
    assert recent_errors()["counts"]["player-cache"] == 3
    assert not set(keys) & {row["key"] for row in store.export_rows("cache")}
    # Real provider jobs can replace the discarded constants and the next HTTP read works.
    assert client.post(f"/player/matches/{MATCH_ID}/refresh").status_code == 200
    PLAYER_SERVICE.jobs.run_pending(until=float("inf"))
    assert store.cache_get("opendota:items")["by_id"]
    store.cache_set(
        keys[1], {"verification_version": COACH_VERSION, "review": {"summary": "restored"}}
    )
    store.cache_set(keys[2], [{"question": "q", "answer": "a", "lang": "ru"}])
    restored = client.get(f"/player/matches/{MATCH_ID}?lang=ru")
    assert restored.status_code == 200
    assert restored.json()["coach"]["review"]["summary"] == "restored"
    assert restored.json()["questions"][0]["question"] == "q"
