"""The public part of a review: picked field by field, nothing that identifies anyone."""

from __future__ import annotations

import json

from match_fixtures import MATCH_ID, ME, ME_STEAM64, FakeOpenDota, opendota_match, recent_matches

from app.player_api import PLAYER_SERVICE
from app.share_review import public_review


def _reviewed(client, tmp_path):
    recent = recent_matches(3)
    fake = FakeOpenDota(
        matches={row["match_id"]: opendota_match(match_id=row["match_id"]) for row in recent},
        recent=recent,
    )
    PLAYER_SERVICE.configure(tmp_path / "svc", client=fake, auto_start=False)
    client.post("/player/link", json={"steam": str(ME)})
    PLAYER_SERVICE.jobs.run_pending(until=float("inf"))


def test_share_payload_has_the_review_and_nothing_personal(client, tmp_path):
    _reviewed(client, tmp_path)
    answer = client.get(f"/player/matches/{MATCH_ID}/share?lang=uk")
    assert answer.status_code == 200
    review = answer.json()["review"]
    assert review["hero"] == "Juggernaut" and review["hero_key"] == "juggernaut"
    assert review["lang"] == "uk" and review["score"] == 90 and review["win"] is True
    assert review["stats"]["kills"] == 11 and review["played_on"] == "2026-09-21"
    assert [s["label"] for s in review["sections"]][:2] == ["Лінія", "Фарм"]
    text = json.dumps(review, ensure_ascii=False)
    # No match id, account, Steam ID, nickname or other players.
    for secret in (str(MATCH_ID), str(ME), ME_STEAM64, "Player 1", "Me"):
        assert secret not in text
    assert "coach" not in review


def test_coach_summary_only_when_asked_and_ready():
    detail = {
        "analysis": {"headline": {"hero": "Lion", "hero_id": 26, "score": 40}},
        "summary": {},
        "coach": {"state": "ready", "review": {"summary": "Lane was lost early."}},
    }
    assert "coach" not in public_review(detail, "en", with_coach=False)
    shared = public_review(detail, "en", with_coach=True)
    assert shared["coach"] == "Lane was lost early." and shared["hero_key"] == "lion"
    detail["coach"]["state"] = "stale"
    assert "coach" not in public_review(detail, "en", with_coach=True)
    assert public_review({"analysis": None}, "en", with_coach=True) is None


def test_share_of_an_unknown_match(client, tmp_path):
    _reviewed(client, tmp_path)
    assert client.get("/player/matches/123/share").status_code == 404


def test_a_match_id_beyond_sqlite_is_rejected_not_a_server_error(client):
    """A 20-digit id overflowed the SQLite integer (HTTP 500) on this route only."""
    answer = client.get("/player/matches/99999999999999999999/share")
    assert answer.status_code == 422
    assert client.get("/player/matches/123/share").status_code == 404
