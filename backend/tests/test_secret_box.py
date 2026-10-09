"""Stored AI/OpenDota keys under OS sealing (secret_box.py): sealed on write,
plain keys of older versions sealed on start, unopenable seals read as missing.
DPAPI itself runs on Windows only (scripts/check_secret_box.py in CI); here a
reversible stand-in plays the OS."""

from __future__ import annotations

import base64
import json
import sqlite3

import pytest

from app.player_api import PLAYER_SERVICE
from app.secret_box import PREFIX, SecretBox

KEY = "gsk_" + "a" * 40
OD_KEY = "12345678-1234-1234-1234-123456789abc"


def _box(user: bytes = b"user-1") -> SecretBox:
    """XOR with a per-user pad: opens only for the same "user"."""

    def flip(data: bytes) -> bytes:
        return bytes(b ^ user[i % len(user)] for i, b in enumerate(data))

    def unprotect(data: bytes) -> bytes:
        if not data.startswith(user):
            raise OSError("other user")
        return flip(data[len(user) :])

    return SecretBox(protect=lambda data: user + flip(data), unprotect=unprotect)


def _raw(service, key: str) -> str | None:
    with sqlite3.connect(service.data_dir / "coach.sqlite3") as conn:
        row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    return row[0] if row else None


def test_keys_are_sealed_on_write_and_read_back(client, tmp_path):
    PLAYER_SERVICE.configure(tmp_path / "svc", auto_start=False, secrets=_box())
    assert client.post("/player/ai", json={"provider": "groq", "api_key": KEY}).status_code == 200
    assert client.post("/player/opendota", json={"api_key": OD_KEY}).status_code == 200
    for meta in ("ai_settings", "opendota_api_key"):
        stored = _raw(PLAYER_SERVICE, meta)
        assert stored.startswith(PREFIX) and KEY not in stored and OD_KEY not in stored
    assert PLAYER_SERVICE.ai_settings().api_key == KEY
    assert PLAYER_SERVICE._opendota_key() == (OD_KEY, "app")
    assert client.get("/player/ai").json()["configured"] is True
    assert PLAYER_SERVICE.secrets_status() == {
        "sealing": "dpapi",
        "sealed": 2,
        "plain": 0,
        "locked": 0,
    }


def test_plain_keys_of_an_older_version_are_sealed_on_start(tmp_path):
    PLAYER_SERVICE.configure(tmp_path / "svc", auto_start=False, secrets=SecretBox())
    PLAYER_SERVICE.set_ai("groq", KEY)
    PLAYER_SERVICE.set_opendota_key(OD_KEY)
    assert _raw(PLAYER_SERVICE, "opendota_api_key") == OD_KEY  # no sealing here
    assert json.loads(_raw(PLAYER_SERVICE, "ai_settings"))["api_key"] == KEY

    PLAYER_SERVICE.configure(tmp_path / "svc", auto_start=False, secrets=_box())
    assert _raw(PLAYER_SERVICE, "opendota_api_key").startswith(PREFIX)
    assert _raw(PLAYER_SERVICE, "ai_settings").startswith(PREFIX)
    assert PLAYER_SERVICE.ai_settings().api_key == KEY
    assert PLAYER_SERVICE._opendota_key()[0] == OD_KEY


def test_a_seal_another_user_made_reads_as_missing(tmp_path):
    PLAYER_SERVICE.configure(tmp_path / "svc", auto_start=False, secrets=_box(b"user-1"))
    PLAYER_SERVICE.set_ai("groq", KEY)
    PLAYER_SERVICE.configure(tmp_path / "svc", auto_start=False, secrets=_box(b"user-2"))
    assert PLAYER_SERVICE.ai_settings() is None
    assert PLAYER_SERVICE.ai_status()["configured"] is False
    assert PLAYER_SERVICE.secrets_status()["locked"] == 1
    # Entering the key again replaces the locked one.
    PLAYER_SERVICE.set_ai("groq", KEY)
    assert PLAYER_SERVICE.ai_settings().api_key == KEY
    assert PLAYER_SERVICE.secrets_status()["locked"] == 0


def test_a_broken_os_seal_keeps_the_plain_key():
    broken = SecretBox(protect=lambda data: b"x" + data, unprotect=lambda data: b"other")
    assert broken.seal(KEY) == KEY
    failing = SecretBox(protect=lambda data: (_ for _ in ()).throw(OSError()), unprotect=bytes)
    assert failing.seal(KEY) == KEY


@pytest.mark.parametrize("value", [PREFIX + "%%%", PREFIX + base64.b64encode(b"junk").decode()])
def test_damaged_seals_open_to_nothing(value):
    assert _box().open(value) is None
    assert SecretBox().open(value) is None  # no OS sealing here at all
    assert SecretBox().open("plain") == "plain"
    assert SecretBox().open(None) is None


def test_the_problem_report_names_the_sealing_without_values(client, tmp_path):
    PLAYER_SERVICE.configure(tmp_path / "svc", auto_start=False, secrets=_box())
    PLAYER_SERVICE.set_ai("groq", KEY)
    report = json.dumps(client.get("/diagnostics").json())
    assert '"sealing": "dpapi"' in report
    assert KEY not in report and PREFIX not in report
