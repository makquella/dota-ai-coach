"""Supports in the advisor: profiles, their saves, what advice they get, their tips."""

from __future__ import annotations

import pytest
from match_fixtures import gsi_match_stream
from test_live_tools import _ability, _extra

from app.gsi_state import _normalize_hero_name
from app.hero_profiles import get_hero_position, get_support_position
from app.live_tools import low_hp_copy
from app.main import SUPPORT_DECISIONS, _covered_decision_point
from app.map_hints import RoleTips, has_observer_ward, map_hint, observer_charges
from app.match_memory import MATCH_MEMORY
from app.player_api import PLAYER_SERVICE
from app.schemas import SUPPORTED_HEROES, hero_coverage

SUPPORTS = [hero for hero in SUPPORTED_HEROES if get_hero_position(hero) == "support"]


def test_twenty_five_supports_of_both_positions():
    assert len(SUPPORTS) == 25
    positions = {get_support_position(hero) for hero in SUPPORTS}
    assert positions == {4, 5}
    assert get_support_position("Juggernaut") is None


@pytest.mark.parametrize(
    ("npc", "hero", "support_position"),
    [
        ("npc_dota_hero_crystal_maiden", "Crystal Maiden", 5),
        ("npc_dota_hero_vengefulspirit", "Vengeful Spirit", 5),
        ("npc_dota_hero_treant", "Treant Protector", 5),
        ("npc_dota_hero_rattletrap", "Clockwerk", 4),
        ("npc_dota_hero_spirit_breaker", "Spirit Breaker", 4),
    ],
)
def test_live_names_positions_and_role_prior(npc, hero, support_position):
    assert _normalize_hero_name(npc) == hero
    assert hero_coverage(hero) == "support"
    assert get_support_position(hero) == support_position
    assert PLAYER_SERVICE.role_prior(hero) == {"role": "support", "source": "hero"}


def test_a_support_gets_survival_fights_and_objectives_but_no_farm_or_items():
    for decision in ("LOW_HP", "DEATH_REVIEW", "HERO_SURVIVABILITY_RISK", "OBJECTIVE_FIGHT_CHECK"):
        assert _covered_decision_point(decision, "support") == decision
    for decision in ("LANING_FARM_CHECK", "FARMING_PHASE_PRESSURE", "SAFE_FARMING", "ITEM_TIMING"):
        assert decision not in SUPPORT_DECISIONS
        assert _covered_decision_point(decision, "support") == "NO_ADVICE"
    # The safety-only heroes still get less than a profiled support.
    assert _covered_decision_point("OBJECTIVE_FIGHT_CHECK", "safety") == "NO_ADVICE"


def test_their_own_saves_at_low_hp():
    mirana = _extra(abilities={"ability0": _ability("mirana_leap")}, hero="npc_dota_hero_mirana")
    assert low_hp_copy(mirana, "Mirana")[0] == "Use Leap now to get out, then reset HP."
    dazzle = _extra(
        abilities={"ability0": _ability("dazzle_shallow_grave")}, hero="npc_dota_hero_dazzle"
    )
    assert low_hp_copy(dazzle, "Dazzle")[0] == "Use Shallow Grave now and walk out of the fight."
    # Bounty Hunter's Shadow Walk is "bounty_hunter_wind_walk" in GSI.
    bounty = _extra(
        abilities={"ability0": _ability("bounty_hunter_wind_walk")},
        hero="npc_dota_hero_bounty_hunter",
    )
    assert (
        low_hp_copy(bounty, "Bounty Hunter")[0] == "Use Shadow Walk now to get out, then reset HP."
    )


def test_observer_charges_from_the_raw_items():
    assert observer_charges(None) is None
    assert observer_charges({"slot0": {"name": "item_tango"}}) == 0
    items = {
        "slot0": {"name": "item_ward_observer", "charges": 2},
        "slot1": {"name": "item_ward_dispenser"},
        "stash0": {"name": "item_ward_observer", "charges": 4},
    }
    assert observer_charges(items) == 3  # the stash does not count


def test_a_dispenser_with_only_sentries_carries_no_observer():
    # The combined dispenser reports its observers as `charges` (sentries as
    # `secondary_charges`): zero observers is a real zero, not a missing count.
    only_sentries = {"slot1": {"name": "item_ward_dispenser", "charges": 0, "secondary_charges": 2}}
    assert observer_charges(only_sentries) == 0
    assert has_observer_ward(only_sentries) is False
    one = {"slot1": {"name": "item_ward_dispenser", "charges": 1, "secondary_charges": 1}}
    assert observer_charges(one) == 1
    assert has_observer_ward(one) is True
    # A broken count still means one ward.
    assert observer_charges({"slot0": {"name": "item_ward_observer", "charges": "x"}}) == 1
    assert observer_charges({"slot0": {"name": "item_ward_observer", "charges": -3}}) == 1


def test_a_ward_kept_in_the_bag_for_two_minutes():
    tips = RoleTips()
    assert tips.tip(300, "support", alive=True, has_ward=True, lang="en", ward_charges=2) is None
    # Buying more keeps the time; nothing placed for two minutes → the tip.
    assert tips.tip(380, "support", alive=True, has_ward=True, lang="en", ward_charges=3) is None
    hint = tips.tip(420, "support", alive=True, has_ward=True, lang="ru", ward_charges=3)
    assert hint["title"] == "Поставьте вард"
    # Placing one restarts the count.
    fresh = RoleTips()
    fresh.tip(300, "support", alive=True, has_ward=True, lang="en", ward_charges=2)
    fresh.tip(400, "support", alive=True, has_ward=True, lang="en", ward_charges=1)
    assert fresh.tip(430, "support", alive=True, has_ward=True, lang="en", ward_charges=1) is None
    # Not for a core.
    core = RoleTips()
    core.tip(300, "carry", alive=True, has_ward=True, lang="en", ward_charges=1)
    assert core.tip(450, "carry", alive=True, has_ward=True, lang="en", ward_charges=1) is None


def test_no_save_item_after_twelve_minutes_with_gold():
    items = ["item_tranquil_boots", "item_magic_wand"]
    hint = RoleTips().tip(
        13 * 60, "support", alive=True, has_ward=True, lang="en", gold=1300, items=items
    )
    assert hint["title"] == "No save item yet"
    # Before 12:00, without the gold, or with a Glimmer Cape: nothing.
    assert (
        RoleTips().tip(
            11 * 60, "support", alive=True, has_ward=True, lang="en", gold=1300, items=items
        )
        is None
    )
    assert (
        RoleTips().tip(
            13 * 60, "support", alive=True, has_ward=True, lang="en", gold=600, items=items
        )
        is None
    )
    glimmer = [*items, "item_glimmer_cape"]
    tip = RoleTips().tip(
        13 * 60, "support", alive=True, has_ward=True, lang="en", gold=1300, items=glimmer
    )
    assert tip is None


def test_map_hint_passes_the_ward_count():
    tips = RoleTips()
    map_hint(3 * 60 + 5, "support", tips, alive=True, has_ward=True, lang="en", ward_charges=1)
    hint = map_hint(
        5 * 60 + 20, "support", tips, alive=True, has_ward=True, lang="en", ward_charges=1
    )
    assert hint is not None and hint["id"].startswith("ward_bag@")


def test_a_live_support_hero_gets_no_farm_advice_through_the_api(client):
    stream = gsi_match_stream(
        match_id=1, minutes=14, lh_per_minute=1.0, death_minutes=(), positions=True
    )
    shown = set()
    for payload in stream:
        payload["hero"]["name"] = "npc_dota_hero_lion"
        client.post("/gsi", json=payload)
        answer = client.get("/overlay/recommendation").json()
        if answer.get("recommendation"):
            shown.add(answer["decision_point"])
    status = client.get("/gsi/status").json()
    assert status["hero_coverage"] == "support"
    assert MATCH_MEMORY.role.role()["role"] == "support"
    assert not shown & {"LANING_FARM_CHECK", "FARMING_PHASE_PRESSURE", "SAFE_FARMING"}
