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
    with_item = core.tip(7 * 60, "ru", gold=1300, alive=True, role="carry", next_item="Battle Fury")
    assert with_item["title"] == "1300 золота не потрачено" and "Battle Fury" in with_item["hint"]
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
