"""Counter items for the player's own hero (hero_items.py, data/heroes/item_plans):
every plan follows the template, and Terrorblade's plan answers each lineup the
way his build and the items' 7.41f mechanics say."""

from __future__ import annotations

import json

import pytest
from match_fixtures import gsi_match_stream
from test_next_item import META
from test_situational_items import _stunned

from app.advice_i18n import translate_uk
from app.death_screen import TEXT as DEATH_TEXT
from app.death_screen import build_death_screen
from app.hero_items import ITEM_PLANS_DIR, WHYS, groups, load_plans, plan_for, validate
from app.map_hints import TIPS
from app.post_laning_coach import SITUATIONAL_BECAUSE, _next_item_copy
from app.situational_items import draft_item, situational_item

GENERIC_WHYS = {"evasion", "illusions", "healing", "break", "magic"}


def _tb(enemies, owned=(), *, position="carry", minute=20, deaths=()):
    return situational_item(
        list(deaths),
        list(owned),
        META,
        enemies=list(enemies),
        position=position,
        minute=minute,
        hero="Terrorblade",
    )


# --- the template: what every plan must have ----------------------------------------


def test_every_plan_follows_the_template():
    plans = load_plans()
    assert plans, "no plans in data/heroes/item_plans"
    known = groups()
    for plan in plans.values():
        assert plan["patch"] and plan["checked"] and plan["sources"]
        for rule in plan["rules"]:
            assert rule["basis"].strip()  # why the item, from the build or the mechanics
            assert rule["enemy"] in known and rule.get("also", "evasion") in known
        # A suppressed counter is a generic one, with the reason it does not fit.
        assert set(plan.get("suppress", {})) <= GENERIC_WHYS


@pytest.mark.parametrize("why", sorted(WHYS))
def test_every_why_has_a_reason_wherever_one_is_shown(why):
    # The draft card, the death screen and the farm advice, in both languages.
    assert set(TIPS[f"draft_{why}"]) == {"en", "uk"}
    assert f"why_{why}" in DEATH_TEXT["en"] and f"why_{why}" in DEATH_TEXT["uk"]
    assert why in SITUATIONAL_BECAUSE


def test_a_broken_plan_is_refused():
    good = json.loads((ITEM_PLANS_DIR / "terrorblade.json").read_text(encoding="utf-8"))
    validate(good)
    broken = [
        {**good, "hero": "Not A Hero"},
        {**good, "positions": ["jungle"]},
        {**good, "rules": [{**good["rules"][0], "enemy": "tanks"}]},
        {**good, "rules": [{**good["rules"][0], "basis": " "}]},
        {**good, "rules": [{**good["rules"][0], "why": "vibes"}]},
        {**good, "rules": [good["rules"][0], good["rules"][0]]},  # the same id twice
        {**good, "suppress": {"illusions": ""}},
    ]
    for plan in broken:
        with pytest.raises(ValueError):
            validate(plan)


# --- Terrorblade ---------------------------------------------------------------------


def test_against_evasion_alone_monkey_king_bar():
    item = _tb(["Phantom Assassin", "Lion", "Axe", "Crystal Maiden"])
    assert (item["key"], item["why"], item["enemy"]) == (
        "monkey_king_bar",
        "evasion",
        "Phantom Assassin",
    )


@pytest.mark.parametrize(
    ("evasive", "escape", "spell"),
    [
        ("Phantom Assassin", "Queen of Pain", "Blink"),
        ("Windranger", "Storm Spirit", "Ball Lightning"),
        ("Phantom Assassin", "Puck", "Phase Shift"),
    ],
)
def test_against_evasion_and_an_escape_bloodthorn(evasive, escape, spell):
    item = _tb([evasive, "Lion", escape, "Axe"])
    assert (item["key"], item["why"]) == ("bloodthorn", "evasion_escape")
    assert (item["enemy"], item["escape"], item["spell"]) == (evasive, escape, spell)


def test_anti_mage_is_no_escape_for_a_silence():
    # Counterspell turns the targeted silence back: Monkey King Bar stays.
    assert _tb(["Phantom Assassin", "Anti-Mage", "Lion", "Axe"])["key"] == "monkey_king_bar"


def test_one_answer_to_evasion_is_enough():
    lineup = ["Phantom Assassin", "Queen of Pain", "Lion", "Axe"]
    assert _tb(lineup, ["item_monkey_king_bar"]) is None
    assert _tb(lineup, ["item_bloodthorn"]) is None


def test_against_healing_his_own_skadi_earlier():
    item = _tb(["Huskar", "Lion", "Axe", "Crystal Maiden"], minute=12)
    assert (item["key"], item["why"], item["enemy"]) == ("skadi", "healing", "Huskar")
    # With Skadi bought, the generic answer to Berserker's Blood comes next.
    assert _tb(["Huskar", "Lion", "Axe", "Crystal Maiden"], ["item_skadi"])["key"] == "silver_edge"


def test_no_maelstrom_for_terrorblade():
    lineup = ["Phantom Lancer", "Lion", "Axe", "Crystal Maiden"]
    assert _tb(lineup) is None
    # Other carries keep the generic counter.
    other = situational_item(
        [], [], META, enemies=lineup, position="carry", minute=20, hero="Juggernaut"
    )
    assert other["key"] == "maelstrom"


def test_other_heroes_and_other_positions_keep_the_generic_counters():
    lineup = ["Phantom Assassin", "Queen of Pain", "Lion", "Axe"]
    jugg = situational_item(
        [], [], META, enemies=lineup, position="carry", minute=20, hero="Juggernaut"
    )
    assert jugg["key"] == "monkey_king_bar"
    assert plan_for("Terrorblade", "mid") is None
    generic_mid = situational_item([], [], META, enemies=lineup, position="mid", minute=20)
    assert _tb(lineup, position="mid") == generic_mid


def test_the_minute_gate_and_the_death_patterns_still_come_first():
    # No single-target disabler (Lion's Hex would make it Linken's Sphere).
    lineup = ["Phantom Assassin", "Queen of Pain", "Crystal Maiden", "Axe"]
    assert _tb(lineup, minute=10) is None  # too early in the match for the counter
    stunned = _tb(lineup, deaths=[_stunned(600), _stunned(900)])
    assert stunned["key"] == "black_king_bar"
    # The draft read names the item to plan for, without the minute gate.
    early = draft_item(lineup, [], META, "carry", "Terrorblade")
    assert early["key"] == "bloodthorn"


def test_bloodthorn_says_why_on_the_card_the_death_screen_and_the_farm_advice():
    item = _tb(["Phantom Assassin", "Queen of Pain", "Lion", "Axe"])
    card = TIPS["draft_evasion_escape"]
    params = {
        "item": item["name"],
        "enemy": item["enemy"],
        "escape": item["escape"],
        "spell": item["spell"],
    }
    assert card["en"][1].format(**params) == (
        "Phantom Assassin dodges attacks and Queen of Pain escapes with Blink: plan Bloodthorn. "
        "Its silence stops Blink, and your attacks and illusions never miss the silenced target."
    )
    assert "Queen of Pain тікає через Blink" in card["uk"][1].format(**params)
    screen = build_death_screen(
        death={"t": 1200, "usable": []},
        place=None,
        respawn=30,
        gold=900,
        buyback_cost=None,
        minute=20,
        next_item={**item, "gold_left": 4000},
        lang="uk",
    )
    assert any("Queen of Pain тікає через Blink" in line for line in screen["lines"])
    state = {"minute": 20, "gold": 900, "extra_context": {"next_item": item, "gpm": 520}}
    action, reason = _next_item_copy(state, state["extra_context"])
    assert action == "Keep farming toward Bloodthorn on the safest waves and camps."
    assert reason == (
        "Phantom Assassin dodges your attacks and Queen of Pain escapes with Blink, and "
        "Bloodthorn silences the escape and never misses a silenced target."
    )
    assert translate_uk(reason) == (
        "Phantom Assassin ухиляється від атак, а Queen of Pain тікає через Blink — "
        "Bloodthorn не дасть утекти й по цілі під тишею не промахується."
    )


def test_the_draft_card_for_terrorblade_reaches_the_overlay(client):
    from app.live_role import set_role_setting

    set_role_setting("carry")
    lineup = {
        f"o{i}": {"image": "minimap_enemyicon", "unitname": f"npc_dota_hero_{name}", "team": 3}
        for i, name in enumerate(("phantom_assassin", "queenofpain", "lion", "axe"))
    }
    texts = []
    for payload in gsi_match_stream(minutes=5, death_minutes=(), step_seconds=5):
        payload["hero"]["name"] = "npc_dota_hero_terrorblade"
        payload["minimap"] = lineup
        client.post("/gsi", json=payload)
        if payload["map"]["clock_time"] >= 180:
            hint = client.get("/overlay/recommendation?lang=en").json().get("map_hint") or {}
            texts.append((hint.get("title"), hint.get("hint")))
    assert (
        "Against their draft: Bloodthorn",
        TIPS["draft_evasion_escape"]["en"][1].format(
            enemy="Phantom Assassin", escape="Queen of Pain", spell="Blink", item="Bloodthorn"
        ),
    ) in texts
