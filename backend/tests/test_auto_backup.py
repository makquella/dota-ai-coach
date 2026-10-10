"""Automatic local copies of the history: weekly and update copies, rotation
within KEEP and the disk budget, a restore preview that writes nothing, the
atomic restore, and the SQLite snapshot before a schema change."""

from __future__ import annotations

import gzip
import sqlite3

from test_coach_ai import MATCH_ID, ME, _reviewed_match

from app import auto_backup, history_backup
from app.auto_backup import AutoBackups
from app.player_api import PLAYER_SERVICE

DAY = 86400.0


class Clock:
    def __init__(self) -> None:
        self.now = 1_791_000_000.0

    def __call__(self) -> float:
        return self.now


def _service(client, tmp_path):
    service = _reviewed_match(client, tmp_path, None)
    clock = Clock()
    service.backups._clock = clock
    return service, clock


def test_weekly_and_update_copies_when_due(client, tmp_path):
    service, clock = _service(client, tmp_path)
    first = client.post("/player/backups/auto").json()
    assert first["reason"] == "weekly" and first["made"]["kind"] == "weekly"
    assert first["made"]["matches"] == 1 and first["made"]["size"] > 0
    assert client.post("/player/backups/auto").json() == {"made": None, "reason": "recent"}
    clock.now += 8 * DAY
    assert client.post("/player/backups/auto").json()["reason"] == "weekly"
    # A new app version: a copy of the history as the old version left it.
    clock.now += 3600
    service.store.set_meta("auto_backup_app_version", "0.53.0")
    assert client.post("/player/backups/auto").json()["reason"] == "update"
    listed = client.get("/player/backups").json()
    assert [item["kind"] for item in listed["items"]] == ["update", "weekly", "weekly"]
    assert listed["enabled"] is True and listed["keep"] == auto_backup.KEEP
    # Turned off: nothing more, and the switch is not part of a history backup.
    assert (
        client.post("/player/backups/settings", json={"enabled": False}).json()["enabled"] is False
    )
    clock.now += 30 * DAY
    assert client.post("/player/backups/auto").json() == {"made": None, "reason": "off"}
    keys = {row["key"] for row in client.get("/player/backup").json()["tables"]["meta"]}
    assert not keys & {"auto_backup", "auto_backup_app_version"}


def test_no_copy_of_an_empty_history(client, tmp_path):
    PLAYER_SERVICE.configure(tmp_path / "empty", client=None, auto_start=False)
    assert client.post("/player/backups/auto").json() == {"made": None, "reason": "empty"}
    assert client.get("/player/backups").json()["items"] == []


def test_rotation_keeps_the_newest_within_count_and_budget(tmp_path, monkeypatch):
    clock = Clock()
    backups = AutoBackups(tmp_path / "backups", clock=clock)
    data = {
        "format": "wardly-backup",
        "counts": {"matches": 3},
        "app_version": "x",
        "pad": "y" * 5000,
    }
    for _ in range(auto_backup.KEEP + 2):
        backups.write(data, "weekly")
        clock.now += DAY
    items = backups.items()
    assert len(items) == auto_backup.KEEP
    newest = items[0]["id"]
    monkeypatch.setattr(auto_backup, "BUDGET_BYTES", 1)
    backups.rotate()
    assert [item["id"] for item in backups.items()] == [newest]  # the newest always stays
    leftovers = sorted(path.name for path in backups.directory.iterdir())
    assert leftovers == sorted([newest, newest.replace(".json.gz", ".info.json")])


def test_preview_writes_nothing_and_restore_merges(client, tmp_path):
    service, _ = _service(client, tmp_path)
    copy = client.post("/player/backups").json()["item"]
    assert copy["kind"] == "manual"
    client.post(f"/player/matches/{MATCH_ID}/note", json={"note": "Не ходити в ліс"})
    with sqlite3.connect(service.data_dir / "coach.sqlite3") as conn:
        conn.execute("DELETE FROM matches WHERE match_id = ?", (MATCH_ID,))
    assert service.store.count_matches(ME) == 0

    preview = client.get(f"/player/backups/{copy['id']}/preview").json()
    assert preview["preview"] is True and preview["matches_in_backup"] == 1
    assert preview["imported"]["matches"]["added"] == 1
    assert service.store.count_matches(ME) == 0, "a preview never writes"

    restored = client.post(f"/player/backups/{copy['id']}/restore").json()
    assert restored["imported"]["matches"]["added"] == 1
    assert service.store.count_matches(ME) == 1
    again = client.get(f"/player/backups/{copy['id']}/preview").json()
    assert again["imported"]["matches"] == {"added": 0, "filled": 0}


def test_unknown_damaged_and_malformed_copies(client, tmp_path):
    service, _ = _service(client, tmp_path)
    assert client.get("/player/backups/nope/preview").status_code == 422
    missing = "wardly-backup-20260101T000000Z-weekly.json.gz"
    assert client.get(f"/player/backups/{missing}/preview").status_code == 404
    assert client.post(f"/player/backups/{missing}/restore").status_code == 404
    damaged = service.backups.directory / "wardly-backup-20260102T000000Z-weekly.json.gz"
    damaged.parent.mkdir(parents=True, exist_ok=True)
    damaged.write_bytes(b"not gzip")
    response = client.get(f"/player/backups/{damaged.name}/preview")
    assert response.status_code == 400 and response.json()["code"] == "not_backup"
    damaged.write_bytes(gzip.compress(b'{"format": "something else"}'))
    assert client.post(f"/player/backups/{damaged.name}/restore").json()["code"] == "not_backup"


def test_a_schema_change_snapshots_the_store_first(client, tmp_path):
    service, _ = _service(client, tmp_path)
    data_dir = service.data_dir
    service.store.set_meta("schema_version", "0")
    PLAYER_SERVICE.configure(data_dir, client=None, auto_start=False)
    snapshots = sorted((data_dir / "backups").glob("coach-pre-schema-0-*.sqlite3"))
    assert len(snapshots) == 1
    with sqlite3.connect(snapshots[0]) as conn:
        assert conn.execute("SELECT COUNT(*) FROM matches").fetchone()[0] == 1
        assert (
            conn.execute("SELECT value FROM meta WHERE key = 'schema_version'").fetchone()[0] == "0"
        )
    # Opened once at the current schema: no second snapshot.
    PLAYER_SERVICE.configure(data_dir, client=None, auto_start=False)
    assert len(list((data_dir / "backups").glob("coach-pre-schema-*.sqlite3"))) == 1


def test_validate_and_preview_share_the_import_rules():
    assert history_backup.validate_backup is not None
    try:
        history_backup.validate_backup({"format": "wardly-backup", "version": 99, "tables": {}})
    except history_backup.BackupError as error:
        assert error.code == "newer_version"
    else:
        raise AssertionError("a newer backup was accepted")
