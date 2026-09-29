"""«Почему этот совет?»: a plain sentence for every decision point that can
reach the player, in both languages, on Home and in the review."""

from __future__ import annotations

import json
from typing import get_args

from app.advice_why import WHY, why
from app.analysis_texts import render_analysis
from app.decision_points import DecisionPoint


def test_every_decision_point_that_shows_advice_has_a_reason_in_both_languages():
    shown = set(get_args(DecisionPoint)) - {"NO_ADVICE"}
    assert shown <= set(WHY), sorted(shown - set(WHY))
    for texts in WHY.values():
        assert texts["ru"] and texts["en"]
        assert texts["ru"] != texts["en"]


def test_unknown_or_missing_decision_points_say_nothing():
    assert why("NO_ADVICE", "ru") is None
    assert why(None, "en") is None
    assert why("SOMETHING_NEW", "ru") is None
    assert why("LOW_HP", "de") == WHY["LOW_HP"]["en"]


def test_recent_advice_says_why(client, repo_root):
    sample = repo_root / "data" / "gsi_samples" / "low_hp_juggernaut.json"
    client.post("/gsi", json=json.loads(sample.read_text(encoding="utf-8")))
    shown = client.get("/overlay/recommendation").json()
    expected = WHY[shown["decision_point"]]

    assert client.get("/advice/recent").json()["items"][0]["why"] == expected["en"]
    assert client.get("/advice/recent?lang=ru").json()["items"][0]["why"] == expected["ru"]


def test_the_review_advice_log_says_why():
    analysis = {
        "advice": [
            {"t": 300, "dp": "LOW_HP", "action": "Back off now.", "reason": "", "mode": "urgent"}
        ]
    }
    assert render_analysis(analysis, "ru")["advice"][0]["why"] == WHY["LOW_HP"]["ru"]
    assert render_analysis(analysis, "en")["advice"][0]["why"] == WHY["LOW_HP"]["en"]
