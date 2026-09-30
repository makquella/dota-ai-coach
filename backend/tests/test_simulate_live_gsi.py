"""The live simulation script and the farm-gap tolerance it helped to find."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from app.post_laning_coach import build_post_laning_advice

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "simulate_live_gsi.py"


def _load_script():
    spec = importlib.util.spec_from_file_location("simulate_live_gsi", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_live_simulation_runs_the_whole_path_on_game_time():
    script = _load_script()
    cards = script.simulate(script.synthetic_stream(14, (7,)), "ru")
    points = [card["decision_point"] for card in cards]
    assert points[0] == "DEATH_REVIEW" and cards[0]["clock"] == 7 * 60 + 1
    # Cards follow the game clock (spacing and lifetimes work on it), and the
    # scheduler clock is restored afterwards.
    assert all(a["clock"] < b["clock"] for a, b in zip(cards, cards[1:], strict=False))
    assert len(cards) <= 4
    assert script.scheduler_module._utcnow is script._real_utcnow


def _farming(minute, last_hits, low):
    return {
        "minute": minute,
        "hp_percent": 90,
        "extra_context": {
            "alive": True,
            "farm_quality": "low",
            "expected_lh_range": [low, low + 30],
            "last_hits": last_hits,
            "hp_pressure_state": "healthy",
        },
    }


def test_one_last_hit_short_of_the_pace_is_not_behind():
    advice = build_post_laning_advice(_farming(21, 129, 130), "SAFE_FARMING")
    assert advice is None or advice.category != "post_laning_farm_recovery"
    behind = build_post_laning_advice(_farming(28, 168, 200), "SAFE_FARMING")
    assert behind.category == "post_laning_farm_recovery"
    assert "168" in behind.action and "200+" in behind.action
