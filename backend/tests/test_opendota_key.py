"""OpenDota API key entered in the launcher: stored locally, never returned, applied to the client."""

from __future__ import annotations

import json

from app.opendota import (
    KEYED_REQUEST_INTERVAL_SECONDS,
    MIN_REQUEST_INTERVAL_SECONDS,
    OpenDotaClient,
)
from app.player_api import PLAYER_SERVICE

KEY = "00000000-aaaa-bbbb-cccc-1234567890ab"


class _Session:
    def __init__(self):
        self.queries = []

    def request(self, method, url, params=None, timeout=None):
        self.queries.append(dict(params or []))

        class _Response:
            status_code = 200

            def json(self):
                return {"profile": {"personaname": "Me"}, "rank_tier": 54}

        return _Response()


def _service(tmp_path, env_key=""):
    session = _Session()
    client = OpenDotaClient("https://api.example", api_key=env_key, session=session, min_interval=0)
    PLAYER_SERVICE.configure(tmp_path / "svc", client=client, auto_start=False)
    return client, session


def test_key_is_saved_applied_and_never_returned(client, tmp_path):
    od, session = _service(tmp_path)
    assert client.get("/player/opendota").json() == {
        "enabled": True,
        "configured": False,
        "source": None,
        "key_hint": "",
    }
    answer = client.post("/player/opendota", json={"api_key": KEY}).json()
    assert answer == {"enabled": True, "configured": True, "source": "app", "key_hint": "…90ab"}
    assert od.api_key == KEY and od.min_interval == KEYED_REQUEST_INTERVAL_SECONDS
    od.player(1)
    assert session.queries[-1]["api_key"] == KEY
    assert client.get("/player").json()["opendota_key"] is True
    everything = json.dumps(
        [client.get("/player/opendota").json(), client.get("/diagnostics").json()]
    )
    assert KEY not in everything

    assert client.delete("/player/opendota").json()["configured"] is False
    assert od.api_key == "" and od.min_interval == MIN_REQUEST_INTERVAL_SECONDS


def test_env_key_is_used_until_one_is_entered(client, tmp_path):
    od, _ = _service(tmp_path, env_key="11111111-2222-3333-4444-555566667777")
    assert client.get("/player/opendota").json()["source"] == "env"
    client.post("/player/opendota", json={"api_key": KEY})
    assert od.api_key == KEY
    client.delete("/player/opendota")
    assert od.api_key.startswith("11111111")


def test_bad_key_is_rejected(client, tmp_path):
    _service(tmp_path)
    for bad in ("", "short", "abc def ghi jkl mno", "x" * 200, "k?api_key=1&y=2abcdefgh"):
        response = client.post("/player/opendota", json={"api_key": bad})
        assert response.status_code == 400 and response.json()["code"] == "bad_opendota_key"
