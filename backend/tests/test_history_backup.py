"""History backup: export everything but the keys, merge it back without overwriting."""

from __future__ import annotations

import json

from match_fixtures import MATCH_ID, ME, FakeOpenDota, opendota_match, recent_matches

from app.player_api import PLAYER_SERVICE

SECRET = "0123456789abcdef0123456789abcdef"


def _history(client, tmp_path, name="old"):
    recent = recent_matches(6)
    fake = FakeOpenDota(
        matches={row["match_id"]: opendota_match(match_id=row["match_id"]) for row in recent},
        recent=recent,
    )
    PLAYER_SERVICE.configure(tmp_path / name, client=fake, auto_start=False)
    client.post("/player/link", json={"steam": str(ME)})
    PLAYER_SERVICE.jobs.run_pending(until=float("inf"))
    client.post("/player/opendota", json={"api_key": SECRET})
    client.post("/player/ai", json={"provider": "gemini", "api_key": "AIza" + SECRET})
    PLAYER_SERVICE.store.cache_set("coach:match:1:uk:x", {"review": {"summary": "text"}})
    PLAYER_SERVICE.store.cache_set("opendota:items", {"by_id": {}})
    return PLAYER_SERVICE


def test_backup_moves_the_history_to_a_new_computer(client, tmp_path):
    _history(client, tmp_path)
    before = client.get(f"/player/matches/{MATCH_ID}?lang=uk").json()
    backup = client.get("/player/backup").json()
    text = json.dumps(backup)
    assert backup["format"] == "wardly-backup" and backup["account_id"] == ME
    assert backup["counts"]["matches"] == 6
    # No key of any kind, no OpenDota meta cache, nothing local to the computer.
    assert SECRET not in text and "AIza" not in text
    meta_keys = {row["key"] for row in backup["tables"]["meta"]}
    assert not meta_keys & {"opendota_api_key", "ai_settings", "primary_account_id"}
    assert [row["key"] for row in backup["tables"]["cache"]] == ["coach:match:1:uk:x"]

    # A fresh install, offline: nothing linked, then the backup.
    PLAYER_SERVICE.configure(tmp_path / "new", client=None, auto_start=False)
    assert client.get("/player").json()["linked"] is False
    result = client.post("/player/backup", json=backup).json()
    assert result["linked"] is True and result["account_id"] == ME
    assert result["imported"]["matches"] == {"added": 6, "filled": 0}
    after = client.get(f"/player/matches/{MATCH_ID}?lang=uk").json()
    assert after["analysis"]["headline"] == before["analysis"]["headline"]
    assert PLAYER_SERVICE.store.cache_get("coach:match:1:uk:x") == {"review": {"summary": "text"}}
    assert client.get("/player/opendota").json().get("configured") is not True

    # The same file again adds nothing.
    again = client.post("/player/backup", json=backup).json()
    assert again["imported"]["matches"] == {"added": 0, "filled": 0}
    assert again["linked"] is False


def test_import_never_overwrites_and_keeps_the_linked_account(client, tmp_path):
    service = _history(client, tmp_path)
    backup = client.get("/player/backup").json()
    row = next(r for r in backup["tables"]["matches"] if r["match_id"] == MATCH_ID)
    row["kills"] = 99  # a different value: the stored one wins
    row["match_id"] = MATCH_ID + 777  # and a new match
    service.store.set_primary(12345, source="manual")
    result = client.post("/player/backup", json=backup).json()
    assert result["linked"] is False and result["account_id"] == 12345
    assert result["imported"]["matches"]["added"] == 1
    assert service.store.get_match(ME, MATCH_ID)["kills"] != 99


def test_not_a_backup(client, tmp_path):
    PLAYER_SERVICE.configure(tmp_path / "svc", client=None, auto_start=False)
    bad = client.post("/player/backup", json={"hello": 1})
    assert bad.status_code == 400 and bad.json()["code"] == "not_backup"
    newer = client.post("/player/backup", json={"format": "wardly-backup", "version": 99})
    assert newer.json()["code"] == "newer_version"
    # Invalid known fields reject the entire file before writing any row.
    odd = {
        "format": "wardly-backup",
        "version": 1,
        "tables": {
            "matches": [
                {"account_id": 1, "match_id": 2, "kills": {"x": 1}, "evil": "DROP"},
                {"account_id": {"nested": 1}, "match_id": 3},
                {"account_id": 1, "match_id": [4]},
            ],
            "meta": [{"key": "opendota_api_key", "value": "stolen"}],
            "sqlite_master": [{"name": "x"}],
        },
    }
    result = client.post("/player/backup", json=odd)
    assert result.status_code == 400 and result.json()["code"] == "not_backup"
    assert PLAYER_SERVICE.store.count_matches(1) == 0
    assert PLAYER_SERVICE.store.get_meta("opendota_api_key") is None
