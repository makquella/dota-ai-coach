"""«Нотатка»: the player's own note on a match (store column, service, API)."""

from __future__ import annotations

import sqlite3

from app.player_api import PLAYER_SERVICE
from app.player_store import _SCHEMA, PlayerStore

ACCOUNT = 52079950


def _stored(service, match_id=7001):
    service.store.set_primary(ACCOUNT, source="test")
    service.store.upsert_match(
        ACCOUNT, match_id, source="opendota", fields={"hero_id": 1, "win": 1}
    )
    return match_id


def test_a_note_is_kept_trimmed_and_shown(client):
    match_id = _stored(PLAYER_SERVICE)
    answer = client.post(f"/player/matches/{match_id}/note", json={"note": "  лагав\n інтернет  "})
    assert answer.status_code == 200 and answer.json()["note"] == "лагав інтернет"
    rows = client.get("/player/matches").json()["items"]
    assert rows[0]["note"] == "лагав інтернет"
    # A sync of the same match never erases it.
    PLAYER_SERVICE.store.upsert_match(ACCOUNT, match_id, source="opendota", fields={"kills": 5})
    assert PLAYER_SERVICE.store.get_match(ACCOUNT, match_id)["note"] == "лагав інтернет"
    # Long text is cut; empty removes it.
    long = client.post(f"/player/matches/{match_id}/note", json={"note": "x" * 500}).json()
    assert len(long["note"]) == 200
    assert (
        client.post(f"/player/matches/{match_id}/note", json={"note": " "}).json()["note"] is None
    )
    assert PLAYER_SERVICE.store.get_match(ACCOUNT, match_id)["note"] is None


def test_unknown_match_and_unlinked(client):
    assert client.post("/player/matches/1/note", json={"note": "a"}).status_code == 409
    _stored(PLAYER_SERVICE)
    answer = client.post("/player/matches/123/note", json={"note": "a"})
    assert answer.status_code == 404 and answer.json()["code"] == "match_not_found"


def test_an_old_database_gets_the_column(tmp_path):
    path = tmp_path / "coach.sqlite3"
    old = _SCHEMA.replace("    items TEXT,\n", "").replace("    note TEXT,\n", "")
    assert "note TEXT" not in old
    with sqlite3.connect(path) as conn:
        conn.executescript(old)
        conn.execute("INSERT INTO matches (account_id, match_id) VALUES (1, 2)")
    store = PlayerStore(path)
    assert store.list_matches(1)[0]["note"] is None
    assert store.set_note(1, 2, "новий білд")
    assert store.get_match(1, 2)["note"] == "новий білд"
    assert not store.set_note(1, 3, "немає такого матчу")
    store.close()


def test_the_backup_carries_the_note(client):
    match_id = _stored(PLAYER_SERVICE)
    PLAYER_SERVICE.set_note(match_id, "з другом")
    backup = client.get("/player/backup").json()
    rows = [row for row in backup["tables"]["matches"] if row["match_id"] == match_id]
    assert rows[0]["note"] == "з другом"
