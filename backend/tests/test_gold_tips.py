"""Gold the player is not spending (app/gold_tips.py): any role, map timers or not."""

import copy

from match_fixtures import gsi_match_stream

from app.gold_tips import STALL_EVERY, STALL_SECONDS, START_WAIT, GoldTips


def _tips(start_clock, items, until, step=5):
    tips = GoldTips()
    for clock in range(start_clock, until + 1, step):
        tips.observe(clock, items(clock))
    return tips


def test_an_empty_bag_at_the_start_is_called_after_a_short_wait():
    tips = _tips(-80, lambda clock: [], -80 + START_WAIT - 5)
    assert tips.tip(-80 + START_WAIT - 5, "en", gold=600, alive=True, role="carry") is None
    tips.observe(-80 + START_WAIT, [])
    hint = tips.tip(-80 + START_WAIT, "ru", gold=625, alive=True, role="support")
    assert hint["title"] == "Купите стартовые предметы" and "600 золота" in hint["hint"]
    # It keeps the card over the game plan.
    assert hint["over_plan"] is True
    # Bought something: no call.
    tips.observe(-60, ["item_tango"])
    assert tips.tip(-60, "en", gold=400, alive=True, role="carry") is None


def test_no_start_call_with_little_gold_dead_or_without_an_items_block():
    tips = _tips(-80, lambda clock: [], -40)
    assert tips.tip(-40, "en", gold=150, alive=True, role="carry") is None
    assert tips.tip(-40, "en", gold=600, alive=False, role="carry") is None
    blind = GoldTips()
    blind.observe(-40, None)
    assert blind.tip(-40, "en", gold=600, alive=True, role="carry") is None


def test_gold_left_unspent_for_two_minutes_is_named_by_role():
    bag = ["item_tango", "item_branches"]
    tips = _tips(3 * 60, lambda clock: bag, 7 * 60)
    support = tips.tip(7 * 60, "en", gold=2510, alive=True, role="support")
    assert support["title"] == "2500 gold unspent" and "wards" in support["hint"]
    core = _tips(3 * 60, lambda clock: bag, 7 * 60)
    bfury = {"key": "bfury", "name": "Battle Fury"}
    with_item = core.tip(7 * 60, "ru", gold=1300, alive=True, role="carry", next_item=bfury)
    assert with_item["title"] == "1300 золота не потрачено" and "Battle Fury" in with_item["hint"]
    assert with_item["items"] == [bfury]
    # The quick-buy step: the part the gold already buys, drawn next to the item.
    part = {"key": "quarterstaff", "name": "Quarterstaff", "cost": 875}
    stepped = _tips(3 * 60, lambda clock: bag, 7 * 60).tip(
        7 * 60, "ru", gold=1300, alive=True, role="carry", next_item=bfury, buy_now=part
    )
    assert "на Quarterstaff (875) золота уже хватает" in stepped["hint"]
    assert [i["key"] for i in stepped["items"]] == ["bfury", "quarterstaff"]
    # A core under its threshold, or a purchase lately: no call.
    assert (
        _tips(3 * 60, lambda clock: bag, 7 * 60).tip(
            7 * 60, "en", gold=1000, alive=True, role="carry"
        )
        is None
    )
    bought = _tips(3 * 60, lambda clock: bag if clock < 6 * 60 else [*bag, "item_boots"], 7 * 60)
    assert STALL_SECONDS > 7 * 60 - 6 * 60
    assert bought.tip(7 * 60, "en", gold=2000, alive=True, role="carry") is None


def test_the_stall_call_repeats_and_keeps_buyback_gold_aside():
    bag = ["item_power_treads"]
    tips = _tips(10 * 60, lambda clock: bag, 13 * 60)
    first = tips.tip(13 * 60, "en", gold=1500, alive=True, role="carry")
    assert first is not None
    assert tips.tip(13 * 60 + 25, "en", gold=1500, alive=True, role="carry") is None
    # (from 15:00 a core keeps up to 2000 for a big item)
    again = tips.tip(13 * 60 + STALL_EVERY, "en", gold=2500, alive=True, role="carry")
    assert again is not None and again["id"] != first["id"]
    late = _tips(30 * 60, lambda clock: bag, 34 * 60)
    # 2600 gold, 1800 of them kept for buyback: 800 spare is under the late threshold.
    assert late.tip(34 * 60, "en", gold=2600, alive=True, role="carry", buyback_cost=1800) is None
    assert late.tip(34 * 60, "en", gold=4200, alive=True, role="carry", buyback_cost=1800)[
        "title"
    ] == ("2400 gold unspent")


def test_the_overlay_calls_an_empty_bag_with_map_timers_off_and_a_locked_support_role(client):
    """The player's report: a bot game, the role locked on support, map timers off,
    no items bought — nothing said."""
    client.post("/settings/advice", json={"map_hints": False, "role": "support"})
    stream = gsi_match_stream(minutes=1, death_minutes=(), step_seconds=5)
    seen = None
    for payload in stream:
        payload = copy.deepcopy(payload)
        payload["items"] = {f"slot{i}": {"name": "empty"} for i in range(9)}
        payload["player"]["gold"] = 625
        client.post("/gsi", json=payload)
        answer = client.get("/overlay/recommendation?lang=en").json()
        hint = answer.get("map_hint")
        if hint and hint["id"].startswith("gold-start"):
            seen = (payload["map"]["clock_time"], hint)
            break
    assert seen is not None, "no empty-bag call"
    clock, hint = seen
    assert hint["title"] == "Buy your starting items"


def test_a_hero_not_spawned_yet_is_not_dead(client):
    """Strategy time reports the picked hero as not alive: no «respawn» card at 00:00."""
    payload = copy.deepcopy(gsi_match_stream(minutes=1, death_minutes=())[0])
    payload["map"]["game_state"] = "DOTA_GAMERULES_STATE_STRATEGY_TIME"
    payload["map"]["clock_time"] = 0
    payload["hero"]["alive"] = False
    client.post("/gsi", json=payload)
    answer = client.get("/overlay/recommendation?lang=en").json()
    assert answer.get("decision_point") not in {"DEATH_REVIEW", "REPEATED_DEATH_PATTERN"}
    action = (answer.get("recommendation") or {}).get("action") or ""
    assert "respawn" not in action.lower()


CONSTANTS = {
    "by_id": {
        "44": "tango",
        "16": "branches",
        "11": "quelling_blade",
        "39": "flask",
        "46": "tpscroll",
        "50": "phase_boots",
        "145": "bfury",
        "147": "manta",
    },
    "items": {
        "tango": {"name": "Tango"},
        "branches": {"name": "Iron Branch"},
        "quelling_blade": {"name": "Quelling Blade"},
        "flask": {"name": "Healing Salve"},
        "tpscroll": {"name": "Town Portal Scroll"},
        "phase_boots": {"name": "Phase Boots", "assembled": True, "cost": 1500},
        "bfury": {"name": "Battle Fury", "assembled": True, "cost": 4100},
        "manta": {"name": "Manta Style", "assembled": True, "cost": 4600},
    },
}


def test_the_usual_start_leaves_out_the_tp_and_rare_buys():
    from app.hero_meta import start_items

    popularity = {
        "start_game_items": {"44": 900, "16": 850, "11": 700, "39": 400, "46": 1000, "50": 10}
    }
    items = start_items(popularity, CONSTANTS)
    assert [item["key"] for item in items] == ["tango", "branches", "quelling_blade", "flask"]
    assert items[0]["name"] == "Tango"
    assert (
        start_items(None, CONSTANTS) == []
        and start_items({"start_game_items": {}}, CONSTANTS) == []
    )


def test_the_start_card_names_the_usual_start_with_icons():
    tips = _tips(-80, lambda clock: [], -60)
    start = [{"key": "tango", "name": "Tango"}, {"key": "quelling_blade", "name": "Quelling Blade"}]
    hint = tips.tip(-60, "ru", gold=625, alive=True, role="carry", start_items=start)
    assert "Обычный старт на этом герое: Tango, Quelling Blade." in hint["hint"]
    assert hint["items"] == start and hint["label"] == "Покупки"


def test_the_plan_carries_the_build_as_icons():
    from app.game_plan import build_items

    meta = {
        "popularity": {"early_game_items": {"50": 50}, "mid_game_items": {"145": 40, "147": 30}},
        "constants": CONSTANTS,
    }
    # Cheap items (boots under the build-item price) are not part of the build.
    assert [item["key"] for item in build_items(meta)] == ["bfury", "manta"]
    assert build_items(None) == []


def test_the_quick_buy_step_is_the_dearest_missing_part_the_gold_buys():
    from app.hero_meta import item_name
    from app.next_item import buy_now, missing_parts

    constants = {
        "items": {
            "bfury": {
                "cost": 4100,
                "components": ["demon_edge", "quelling_blade", "ring_of_health", "void_stone"],
            },
            "demon_edge": {"cost": 2200},
            "quelling_blade": {"cost": 100},
            "ring_of_health": {"cost": 700},
            "void_stone": {"cost": 700},
            "perseverance": {"cost": 1400, "components": ["ring_of_health", "void_stone"]},
        }
    }
    from collections import Counter

    assert missing_parts("bfury", Counter({"quelling_blade": 1}), constants) == [
        ("demon_edge", 2200),
        ("ring_of_health", 700),
        ("void_stone", 700),
    ]
    assert buy_now("bfury", ["item_quelling_blade"], constants, 2300)["key"] == "demon_edge"
    assert buy_now("bfury", ["item_quelling_blade"], constants, 900)["key"] == "ring_of_health"
    assert buy_now("bfury", ["item_quelling_blade"], constants, 50) is None
    # Every part there, only the recipe left: the item at the recipe's price.
    constants["items"]["bfury"]["cost"] = 4300
    owned = ["item_quelling_blade", "item_demon_edge", "item_ring_of_health", "item_void_stone"]
    assert buy_now("bfury", owned, constants, 700) == {
        "key": "bfury",
        "name": item_name("bfury", constants),
        "cost": 600,
    }


def test_strategy_time_names_the_start_at_once():
    """The shop opens with the pick: no wait while the hero is not on the map yet."""
    tips = GoldTips()
    tips.observe(-90, [])
    start = [{"key": "tango", "name": "Tango"}]
    assert tips.tip(-90, "en", gold=600, alive=True, role="mid", start_items=start) is None
    hint = tips.tip(-90, "en", gold=600, alive=True, role="mid", start_items=start, pre_spawn=True)
    assert hint["items"] == start and hint["over_plan"] is True


def test_the_overlay_shows_the_start_in_strategy_time(client):
    payload = copy.deepcopy(gsi_match_stream(minutes=1, death_minutes=())[0])
    payload["map"]["game_state"] = "DOTA_GAMERULES_STATE_STRATEGY_TIME"
    payload["map"]["clock_time"] = -100
    payload["hero"]["alive"] = False
    payload["items"] = {f"slot{i}": {"name": "empty"} for i in range(9)}
    payload["player"]["gold"] = 600
    client.post("/gsi", json=payload)
    hint = client.get("/overlay/recommendation?lang=ru").json().get("map_hint")
    assert hint is not None and hint["title"] == "Купите стартовые предметы"


def test_the_spawn_tick_of_the_pre_game_is_not_a_death(client):
    """A recorded bot game: the first PRE_GAME tick (-1:28) had the hero not alive,
    0 deaths, 0 s to respawn — and a «plan a safer route» card came."""
    payload = copy.deepcopy(gsi_match_stream(minutes=1, death_minutes=())[0])
    payload["map"]["game_state"] = "DOTA_GAMERULES_STATE_PRE_GAME"
    payload["map"]["clock_time"] = -88
    payload["hero"]["alive"] = False
    payload["hero"]["respawn_seconds"] = 0
    payload["player"]["deaths"] = 0
    client.post("/gsi", json=payload)
    answer = client.get("/overlay/recommendation?lang=en").json()
    assert answer.get("decision_point") not in {"DEATH_REVIEW", "REPEATED_DEATH_PATTERN"}
    # A real death (counted) stays a death.
    payload["map"]["game_state"] = "DOTA_GAMERULES_STATE_GAME_IN_PROGRESS"
    payload["map"]["clock_time"] = 300
    payload["player"]["deaths"] = 1
    payload["hero"]["respawn_seconds"] = 20
    client.post("/gsi", json=payload)
    from app.gsi_state import get_current_state

    assert get_current_state()["state"]["extra_context"]["alive"] is False
