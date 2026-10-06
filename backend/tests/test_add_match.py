"""0.51: a match older than the synced history, opened by its number."""

from __future__ import annotations

from match_fixtures import ME, FakeOpenDota, opendota_match, recent_matches

from app.player_api import PLAYER_SERVICE

OLD = 7000000001  # not among the recent matches
STRANGER = 7000000002  # the player is not in it
TURBO = 7000000003


def _service(client, tmp_path):
    recent = recent_matches(3)
    old = opendota_match(good=True, match_id=OLD)
    stranger = opendota_match(good=True, match_id=STRANGER)
    for player in stranger["players"]:
        if player.get("account_id") == ME:
            player["account_id"] = 42
    turbo = opendota_match(good=True, match_id=TURBO)
    turbo["game_mode"] = 23
    fake = FakeOpenDota(matches={OLD: old, STRANGER: stranger, TURBO: turbo}, recent=recent)
    PLAYER_SERVICE.configure(tmp_path / "svc", client=fake, auto_start=False)
    client.post("/player/link", json={"steam": str(ME)})
    PLAYER_SERVICE.jobs.run_pending(until=float("inf"))
    return fake


def _add(client, match_id):
    first = client.post(f"/player/matches/{match_id}/add").json()
    PLAYER_SERVICE.jobs.run_pending(until=float("inf"))
    return first, client.get(f"/player/matches/{match_id}/add").json()


def test_an_older_match_is_fetched_and_reviewed(client, tmp_path):
    _service(client, tmp_path)
    assert client.get(f"/player/matches/{OLD}?lang=ru").status_code == 404
    first, after = _add(client, OLD)
    assert first == {"state": "pending"} and after == {"state": "ready"}
    detail = client.get(f"/player/matches/{OLD}?lang=ru").json()
    assert detail["analysis"] and detail["summary"]["hero"] == "Juggernaut"
    # Asked again: it is there, nothing fetched twice.
    assert client.post(f"/player/matches/{OLD}/add").json() == {"state": "ready"}


def test_a_match_without_the_player_or_in_turbo_is_not_kept(client, tmp_path):
    _service(client, tmp_path)
    assert _add(client, STRANGER)[1] == {"state": "not_player"}
    assert _add(client, TURBO)[1] == {"state": "mode"}
    assert _add(client, 7000000099)[1] == {"state": "not_found"}
    ids = {row["match_id"] for row in client.get("/player/matches?limit=50").json()["items"]}
    assert not ids & {STRANGER, TURBO, 7000000099}
    # An error is no dead end: asking again tries again.
    assert client.post(f"/player/matches/{STRANGER}/add").json() == {"state": "pending"}


def test_unlinked_and_offline(client, tmp_path):
    PLAYER_SERVICE.configure(tmp_path / "svc", client=None, auto_start=False)
    assert client.post(f"/player/matches/{OLD}/add").json() == {"state": "unlinked"}
    client.post("/player/link", json={"steam": str(ME)})
    assert client.post(f"/player/matches/{OLD}/add").json() == {"state": "offline"}
    assert client.get(f"/player/matches/{OLD}/add").json() == {"state": "none"}
