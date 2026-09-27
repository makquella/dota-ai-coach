"""Turbo, bot games and other modes with their own rules stay out of the history."""

from __future__ import annotations

from match_fixtures import (
    MATCH_ID,
    ME,
    FakeOpenDota,
    gsi_match_stream,
    opendota_match,
    recent_matches,
)

from app.dota_constants import is_reviewable_match
from app.player_api import PLAYER_SERVICE


def test_reviewable_modes():
    assert is_reviewable_match({"game_mode": 22, "lobby_type": 7})
    assert is_reviewable_match({"game_mode": None, "lobby_type": None})
    assert not is_reviewable_match({"game_mode": 23, "lobby_type": 0})  # Turbo
    assert not is_reviewable_match({"game_mode": 18, "lobby_type": 0})  # Ability Draft
    assert not is_reviewable_match({"game_mode": 22, "lobby_type": 4})  # co-op bots


def test_sync_skips_turbo_and_says_how_many(client, tmp_path):
    recent = recent_matches(10)
    for row in recent[:3]:
        row["game_mode"] = 23
    recent[3]["game_mode"] = 18
    PLAYER_SERVICE.configure(tmp_path / "svc", client=FakeOpenDota(recent=recent), auto_start=False)
    # An older version kept a Turbo match: the next sync drops it.
    PLAYER_SERVICE.store.upsert_match(
        ME, 1234, source="opendota", fields={"game_mode": 23, "lobby_type": 0, "hero_id": 8}
    )
    client.post("/player/link", json={"steam": str(ME)})
    PLAYER_SERVICE.jobs.run_pending(until=float("inf"))

    matches = client.get("/player/matches").json()
    assert matches["total"] == 6
    assert {m["match_id"] for m in matches["items"]} == {r["match_id"] for r in recent[4:]}
    assert matches["skipped"] == {"count": 4, "turbo": 3, "of": 10}


def test_a_live_turbo_match_leaves_the_history_once_opendota_names_the_mode(client, tmp_path):
    turbo = opendota_match(good=True)
    turbo["game_mode"] = 23
    fake = FakeOpenDota(matches={MATCH_ID: turbo})
    PLAYER_SERVICE.configure(tmp_path / "svc", client=fake, auto_start=False)
    for payload in gsi_match_stream(minutes=10):
        client.post("/gsi", json=payload)
    # Reviewed offline from GSI at once (GSI does not tell the mode)...
    assert [m["match_id"] for m in client.get("/player/matches").json()["items"]] == [MATCH_ID]
    # ...and removed when OpenDota shows it was Turbo.
    PLAYER_SERVICE.jobs.run_pending(until=float("inf"))
    assert client.get("/player/matches").json()["items"] == []
    assert client.get("/player/matches").json()["skipped"] is None
