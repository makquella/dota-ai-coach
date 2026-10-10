"""Lane tips for cores in the first ten minutes (map_hints.RoleTips._lane)."""

from __future__ import annotations

import copy

from match_fixtures import gsi_match_stream

from app.map_hints import (
    DENY_AT,
    LANE_HP_EVERY,
    LANE_REGEN_UNTIL,
    STICK_FROM,
    RoleTips,
)


def _tip(tips, clock, role="carry", **kw):
    base = {"alive": True, "has_ward": None, "lang": "uk"}
    return tips.tip(clock, role, **{**base, **kw})


def test_no_regen_on_the_way_to_lane():
    tips = RoleTips()
    tip = _tip(tips, 10, items=["item_quelling_blade", "item_slippers"])
    assert tip["title"] == "Немає регену на лінію"
    assert _tip(RoleTips(), 10, items=["item_tango", "item_quelling_blade"]) is None
    assert _tip(RoleTips(), LANE_REGEN_UNTIL + 1, items=["item_slippers"]) is None
    assert _tip(RoleTips(), 10, items=None) is None  # no items block: nothing claimed
    # A support gets its own tips, not the cores' lane ones.
    assert _tip(RoleTips(), 10, role="support", items=["item_ward_observer"]) is None


def test_half_hp_with_nothing_to_heal():
    tips = RoleTips()
    kw = {"hp": 42, "regen": [], "gold": 300, "items": ["item_magic_stick"]}
    tip = _tip(tips, 200, **kw)
    assert tip["title"] == "42% HP і нічим лікуватися"
    # The number of the first second stays; then quiet until LANE_HP_EVERY passes.
    assert _tip(tips, 205, **{**kw, "hp": 35})["title"] == "42% HP і нічим лікуватися"
    assert _tip(tips, 260, **kw) is None
    assert _tip(tips, 200 + LANE_HP_EVERY, **kw) is not None
    assert _tip(RoleTips(), 200, **{**kw, "regen": ["item_flask"]}) is None
    assert _tip(RoleTips(), 200, **{**kw, "gold": 50}) is None
    assert _tip(RoleTips(), 200, **{**kw, "hp": 70}) is None
    assert _tip(RoleTips(), 11 * 60, **kw) is None  # after the lane


def test_a_magic_stick_by_mid_lane_once():
    tips = RoleTips()
    kw = {"items": ["item_tango", "item_quelling_blade"], "gold": 250}
    tip = _tip(tips, STICK_FROM, **kw)
    assert tip["title"] == "Ще немає Magic Stick"
    assert _tip(tips, STICK_FROM + 60, **kw) is None  # once
    assert _tip(RoleTips(), STICK_FROM, **{**kw, "items": ["item_magic_wand"]}) is None
    assert _tip(RoleTips(), STICK_FROM, **{**kw, "gold": 150}) is None


def test_denies_at_four_minutes_for_a_carry_or_a_mid():
    kw = {"denies": 1, "last_hits": 14, "items": ["item_tango", "item_magic_stick"], "gold": 50}
    tip = _tip(RoleTips(), DENY_AT + 2, **kw)
    assert tip["title"] == "Денаїв до 4:00: 1"
    assert _tip(RoleTips(), DENY_AT + 2, role="mid", **kw)["id"] == f"lane_denies@{DENY_AT}"
    assert _tip(RoleTips(), DENY_AT + 2, role="offlane", **kw) is None
    assert _tip(RoleTips(), DENY_AT + 2, **{**kw, "denies": 5}) is None
    assert _tip(RoleTips(), DENY_AT + 2, **{**kw, "last_hits": 3}) is None


def test_lane_tips_reach_the_overlay(client):
    from app.live_role import set_role_setting

    set_role_setting("carry")
    payload = copy.deepcopy(gsi_match_stream(minutes=1, death_minutes=())[0])
    payload["map"]["clock_time"] = 20
    payload["map"]["game_time"] = 110
    payload["items"] = {
        "slot0": {"name": "item_quelling_blade"},
        "slot1": {"name": "item_slippers"},
    }
    client.post("/gsi", json=payload)
    body = client.get("/overlay/recommendation?lang=en").json()
    assert body["map_hint"]["title"] == "No regen for the lane"
