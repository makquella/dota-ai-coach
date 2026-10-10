"""Every death with its context: where, who, unspent gold, the warning before it."""

from __future__ import annotations

from app.advice_context import MAP_CENTER
from app.analysis_texts import render_analysis
from app.death_review import review_deaths, zone


def _at(x, y):
    return MAP_CENTER + x, MAP_CENTER + y


def test_zones_of_the_map():
    assert zone(*_at(-6400, 2000)) == "top"
    assert zone(*_at(3000, -6400)) == "bot"
    assert zone(*_at(300, 100)) == "mid"
    assert zone(*_at(-2500, 2000)) == "jungle"
    assert zone(*_at(-7000, -6800)) == "base"


def test_each_death_with_what_is_known():
    x, y = _at(1000, 3000)
    facts = {
        "is_radiant": True,
        "deaths_log": [
            {"t": 420, "killer": "Axe", "gold": 350, "respawn": 30},
            {"t": 480, "gold": 1800, "x": x, "y": y, "respawn": 40},
            {"t": 1500},
        ],
        "advice_log": [
            {
                "t": 400,
                "action": "Leave the wave now and reset HP before rejoining.",
                "mode": "urgent",
            },
            {"t": 1000, "action": "Something long ago.", "mode": "coaching"},
        ],
    }
    block = review_deaths(facts)
    first, second, third = block["deaths"]
    assert (
        first["killer"] == "Axe" and first["warning"]["t"] == 400 and first["notes"] == ["warned"]
    )
    assert first["phase"] == "laning" and "zone" not in first
    # Respawned at 450, dead again 30 s later, with 1800 gold, on the Dire half.
    assert second["after_respawn"] == 30
    assert second["side"] == "enemy" and second["zone"] == "jungle"
    assert set(second["notes"]) == {"enemy_half", "unspent_gold", "soon_after_respawn"}
    assert third["notes"] == [] and third["phase"] == "late"
    assert block["notes"] == {
        "warned": 1,
        "enemy_half": 1,
        "unspent_gold": 1,
        "soon_after_respawn": 1,
    }
    assert review_deaths({"deaths_log": []}) is None
    # The warning is shown in the review language.
    uk = render_analysis({"death_review": block}, "uk")["death_review"]["deaths"][0]
    assert uk["warning"]["action"] != first["warning"]["action"]
