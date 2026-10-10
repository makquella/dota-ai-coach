"""Counter items: the enemy heroes seen on the minimap (enemy_heroes.py) and how
the player dies pick the next item (situational_items.py)."""

from __future__ import annotations

from match_fixtures import gsi_match_stream
from test_situational_items import META, _stunned

from app.advice_i18n import translate_uk
from app.enemy_heroes import EnemyHeroes, visible_enemy_heroes
from app.gsi_state import _normalize_hero_name
from app.map_hints import RoleTips
from app.match_memory import MATCH_MEMORY
from app.post_laning_coach import _next_item_copy
from app.situational_items import situational_item


def _minimap(*units):
    return {f"o{i}": unit for i, unit in enumerate(units)}


def test_the_minimap_shows_the_enemy_heroes_the_team_can_see():
    minimap = _minimap(
        {"unitname": "npc_dota_hero_beastmaster", "team": 3},
        {"unitname": "npc_dota_hero_queenofpain", "team": 2},  # own team
        {"unitname": "npc_dota_creep_badguys_melee", "team": 3},  # not a hero
        {"unitname": "npc_dota_hero_nevermore", "team": "3"},  # a broken team
        {"unitname": 12, "team": 3},
        "junk",
    )
    assert visible_enemy_heroes(minimap, "radiant", _normalize_hero_name) == ["Beastmaster"]
    assert visible_enemy_heroes(minimap, None, _normalize_hero_name) is None  # team unknown
    assert visible_enemy_heroes(None, "radiant", _normalize_hero_name) is None  # no block
    seen = EnemyHeroes()
    seen.observe(["Beastmaster"])
    seen.observe(["Lion", "Beastmaster", 3])
    seen.observe("Axe")
    assert seen.heroes() == ["Beastmaster", "Lion"]
    for name in ["Axe", "Riki", "Zeus", "Pudge"]:
        seen.observe([name])
    assert len(seen.heroes()) == 5  # a lineup, not every name GSI ever sends


def test_live_gsi_remembers_the_enemies_for_the_match(client):
    for payload in gsi_match_stream(minutes=8, death_minutes=()):
        if payload["map"]["clock_time"] == 300:
            payload["minimap"] = _minimap({"unitname": "npc_dota_hero_beastmaster", "team": 3})
        client.post("/gsi", json=payload)
    # Seen once at 5:00, still known later in the match.
    assert MATCH_MEMORY.enemies.heroes() == ["Beastmaster"]


def test_deaths_under_stuns_against_a_targeted_disable_ask_for_linkens():
    """A Queen of Pain kept dying to Primal Roar, which goes through BKB."""
    deaths = [_stunned(600), _stunned(1300)]
    item = situational_item(deaths, [], META, enemies=["Beastmaster"], position="mid")
    assert item["key"] == "sphere" and item["name"] == "Linken's Sphere"
    assert item["why"] == "targeted" and item["enemy"] == "Beastmaster"
    assert item["spell"] == "Primal Roar" and item["count"] == 2
    # Without such a hero among the enemies: Black King Bar, as before.
    assert situational_item(deaths, [], META, enemies=["Axe"], position="mid")["key"] == (
        "black_king_bar"
    )
    # Linken's already owned: the next answer.
    owned = situational_item(deaths, ["item_sphere"], META, enemies=["Beastmaster"], position="mid")
    assert owned["key"] == "black_king_bar"
    # A support is not told to buy Linken's.
    support = situational_item(deaths, [], META, enemies=["Beastmaster"], position="support")
    assert support["key"] == "black_king_bar"


def test_counters_to_the_enemy_heroes_seen():
    carry = situational_item(
        [], [], META, enemies=["Phantom Assassin"], position="carry", minute=16
    )
    assert carry["key"] == "monkey_king_bar" and carry["why"] == "evasion"
    assert carry["enemy"] == "Phantom Assassin"
    # Too early, or a hero who does not hit with attacks: the usual build.
    assert (
        situational_item([], [], META, enemies=["Phantom Assassin"], position="carry", minute=10)
        is None
    )
    assert (
        situational_item([], [], META, enemies=["Phantom Assassin"], position="mid", minute=20)
        is None
    )
    offlane = situational_item([], [], META, enemies=["Huskar"], position="offlane", minute=14)
    assert offlane["key"] == "spirit_vessel" and offlane["why"] == "healing"


def test_the_card_and_the_death_screen_say_why():
    from app.death_screen import build_death_screen

    item = {
        "key": "sphere",
        "name": "Linken's Sphere",
        "cost": 4600,
        "gold_left": 2800,
        "why": "targeted",
        "count": 3,
        "enemy": "Beastmaster",
        "spell": "Primal Roar",
    }
    state = {"minute": 20, "gold": 900, "extra_context": {"next_item": item, "gpm": 520}}
    action, reason = _next_item_copy(state, state["extra_context"])
    assert action == "Keep farming toward Linken's Sphere on the safest waves and camps."
    assert reason.startswith(
        "3 deaths under stuns against Beastmaster, and Linken's Sphere blocks Primal Roar"
    )
    assert translate_uk(reason).startswith(
        "3 смерті під контролем проти Beastmaster — Linken's Sphere блокує Primal Roar: бракує 1900 золота"
    )
    mkb = {
        **item,
        "key": "monkey_king_bar",
        "name": "Monkey King Bar",
        "why": "evasion",
        "count": 0,
        "enemy": "Phantom Assassin",
        "spell": None,
    }
    state = {"minute": 20, "gold": 900, "extra_context": {"next_item": mkb, "gpm": 520}}
    _, reason = _next_item_copy(state, state["extra_context"])
    assert translate_uk(reason).startswith(
        "Phantom Assassin ухиляється від атак — Monkey King Bar б'є без промаху"
    )
    card = build_death_screen(
        death={"t": 1200, "usable": []},
        place=None,
        respawn=30,
        gold=900,
        buyback_cost=None,
        minute=20,
        next_item=item,
        lang="uk",
    )
    assert any("проти Beastmaster" in line and "Primal Roar" in line for line in card["lines"])


def test_a_support_is_told_to_carry_dust_against_an_invisible_hero():
    tips = RoleTips()
    tip = tips.tip(
        7 * 60,
        "support",
        alive=True,
        has_ward=True,
        lang="uk",
        items=["item_tango"],
        enemies=["Riki"],
    )
    assert tip["title"] == "Riki іде в невидимість"
    assert "Dust of Appearance" in tip["hint"]
    # Dust or a sentry carried, before 6:00, or no invisible hero: nothing.
    assert (
        RoleTips().tip(
            7 * 60,
            "support",
            alive=True,
            has_ward=True,
            lang="uk",
            items=["item_dust"],
            enemies=["Riki"],
        )
        is None
    )
    assert (
        RoleTips().tip(
            5 * 60 + 30, "support", alive=True, has_ward=True, lang="uk", items=[], enemies=["Riki"]
        )
        is None
    )
    assert (
        RoleTips().tip(
            7 * 60, "support", alive=True, has_ward=True, lang="uk", items=[], enemies=["Axe"]
        )
        is None
    )


def test_illusion_heroes_ask_a_carry_for_maelstrom():
    from app.death_screen import build_death_screen

    item = situational_item([], [], META, enemies=["Phantom Lancer"], position="carry", minute=13)
    assert item["key"] == "maelstrom" and item["why"] == "illusions"
    assert item["enemy"] == "Phantom Lancer"
    # A mid, or before minute 12: the usual build.
    assert situational_item([], [], META, enemies=["Naga Siren"], position="mid", minute=20) is None
    assert (
        situational_item([], [], META, enemies=["Naga Siren"], position="carry", minute=11) is None
    )
    state = {"minute": 13, "gold": 400, "extra_context": {"next_item": item, "gpm": 480}}
    _, reason = _next_item_copy(state, state["extra_context"])
    assert reason.startswith("Phantom Lancer fights with illusions, and Maelstrom hits them all")
    assert translate_uk(reason).startswith(
        "Phantom Lancer б'ється ілюзіями — Maelstrom б'є їх усіх одразу"
    )
    card = build_death_screen(
        death={"t": 800, "usable": []},
        place=None,
        respawn=20,
        gold=1500,
        buyback_cost=None,
        minute=13,
        next_item=item,
        lang="uk",
    )
    assert any("б'ється ілюзіями" in line for line in card["lines"])


def test_more_single_target_disables_are_known():
    # Spirit Breaker's Charge goes through BKB, Linken's blocks it.
    deaths = [_stunned(900), _stunned(1500)]
    item = situational_item(deaths, [], META, enemies=["Spirit Breaker"], position="carry")
    assert item["key"] == "sphere" and item["spell"] == "Charge of Darkness"
