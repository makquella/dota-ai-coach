"""Every hero gets survival advice; farm/item/objective advice stays with the carry advisor."""

from __future__ import annotations

import copy
import json

import pytest

from app.main import SAFETY_ONLY_DECISIONS, _covered_decision_point
from app.schemas import GameSituationRequest, hero_coverage, safety_only_hero

SAMPLES = "data/gsi_samples"


@pytest.mark.parametrize(
    ("name", "coverage", "canonical"),
    [
        ("Juggernaut", "full", None),
        ("Crystal Maiden", "safety", "Crystal Maiden"),
        ("Furion", "safety", "Nature's Prophet"),  # live GSI title-cases the npc name
        ("Wisp", "safety", "Io"),
        ("Unknown", None, None),
        ("", None, None),
    ],
)
def test_coverage(name, coverage, canonical):
    assert hero_coverage(name) == coverage
    assert safety_only_hero(name) == canonical


def test_request_accepts_any_hero_by_canonical_name():
    request = GameSituationRequest(
        hero="Furion",
        role="carry",
        minute=12,
        level=10,
        gold=300,
        items=[],
        hp_percent=20,
        game_state="laning",
        team_status="even",
    )
    assert request.hero == "Nature's Prophet"
    with pytest.raises(ValueError):
        GameSituationRequest(**{**request.model_dump(), "hero": "Not A Hero"})


def test_only_survival_decisions_pass_for_other_heroes():
    for decision in (
        "FARMING_PHASE_PRESSURE",
        "ITEM_TIMING",
        "OBJECTIVE_FIGHT_CHECK",
        "LANING_FARM_CHECK",
    ):
        assert _covered_decision_point(decision, "safety") == "NO_ADVICE"
        assert _covered_decision_point(decision, "full") == decision
    for decision in ("LOW_HP", "DEATH_REVIEW", "DISABLED_STATUS"):
        assert decision in SAFETY_ONLY_DECISIONS
        assert _covered_decision_point(decision, "safety") == decision


def _as_hero(payload: dict, npc: str) -> dict:
    payload = copy.deepcopy(payload)
    payload.setdefault("hero", {})["name"] = npc
    return payload


def test_low_hp_advice_for_a_support(client, repo_root):
    payload = json.loads(
        (repo_root / SAMPLES / "low_hp_juggernaut.json").read_text(encoding="utf-8")
    )
    client.post("/gsi", json=_as_hero(payload, "npc_dota_hero_crystal_maiden"))
    overlay = client.get("/overlay/recommendation").json()
    assert overlay["hero_coverage"] == "safety"
    assert overlay["status"] != "unsupported_hero"
    assert overlay["decision_point"] in SAFETY_ONLY_DECISIONS
    assert overlay["recommendation"] is not None
    assert overlay["advice_mode"] == "urgent"


def test_farm_advice_is_held_back_for_a_support(client, repo_root):
    payload = json.loads((repo_root / SAMPLES / "low_farm_rate.json").read_text(encoding="utf-8"))
    client.post("/gsi", json=payload)
    full = client.get("/overlay/recommendation").json()
    client.post("/session/reset")
    client.post("/gsi", json=_as_hero(payload, "npc_dota_hero_crystal_maiden"))
    support = client.get("/overlay/recommendation").json()
    assert support["hero_coverage"] == "safety"
    if full["decision_point"] not in SAFETY_ONLY_DECISIONS:
        assert support["decision_point"] == "NO_ADVICE"
        assert support["recommendation"] is None
