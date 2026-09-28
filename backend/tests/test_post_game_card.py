"""The overlay's match summary on Dota's score screen (post_game.py)."""

from __future__ import annotations

import copy

from match_fixtures import MATCH_ID, gsi_match_stream

from app.player_api import PLAYER_SERVICE
from app.post_game import post_game_card


def test_score_screen_shows_the_summary_of_the_match_just_played(client, tmp_path):
    PLAYER_SERVICE.configure(tmp_path / "svc", client=None, auto_start=False)
    stream = gsi_match_stream(win=False)
    for payload in stream[:-1]:
        client.post("/gsi", json=payload)
    # In the match: no summary yet.
    assert "post_game" not in client.get("/overlay/recommendation?lang=ru").json()
    assert client.get("/gsi/status").json()["post_game"] is False

    client.post("/gsi", json=stream[-1])  # POST_GAME: the match is reviewed at once
    status = client.get("/gsi/status").json()
    assert status["post_game"] is True and status["in_match"] is False
    card = client.get("/overlay/recommendation?lang=ru").json()["post_game"]
    assert card["title"] == "Итог матча" and card["hero"] == "Juggernaut"
    assert card["result"] == "Поражение" and card["win"] is False
    assert card["score_text"] == f"{card['score']}/100"
    assert card["main"].startswith("Главное: ") and len(card["detail"]) == 2
    assert card["detail"][-1] == "Полный разбор — в приложении."
    english = client.get("/overlay/recommendation?lang=en").json()["post_game"]
    assert english["title"] == "Match summary"

    # Another match's score screen (a replay, the next game): nothing.
    other = copy.deepcopy(stream[-1])
    other["map"]["matchid"] = str(MATCH_ID + 5)
    client.post("/gsi", json=other)
    assert "post_game" not in client.get("/overlay/recommendation").json()


def test_card_needs_a_score_and_names_the_focus():
    analysis = {
        "headline": {"score": 71.6, "win": True, "hero": "Lina", "grade": "B"},
        "improvements": [{"id": "deaths_high", "section": "survival", "params": {"deaths": 9}}],
        "strengths": [],
    }
    card = post_game_card(analysis, "en", focus_met=True)
    assert card["score"] == 72 and card["result"] == "Win"
    assert card["main"].startswith("Main point: ")
    assert card["detail"][0] == "Focus met."
    assert card["detail"][-1] == "The full review is in the app."
    assert post_game_card({"headline": {}}, "en") is None
