"""A rune kept in the Bottle (GSI items.slot*.contains_rune): a way out at low
HP, a heal only when it is a Regeneration or Water rune, and a kill to make
for a hero who keeps a power rune in it (map_hints)."""

from __future__ import annotations

import copy

from match_fixtures import gsi_match_stream

from app.advice_i18n import translate_ru
from app.advice_text import clean_reason_text
from app.gsi_census import GsiCensus
from app.gsi_state import normalize_gsi_payload
from app.live_tools import bottle_rune, low_hp_copy, regen_items
from app.map_hints import BOTTLE_RUNE_HELD, BOTTLE_RUNE_SHOW, RoleTips, map_hint


def _bottle(rune, charges=2):
    return {"name": "item_bottle", "charges": charges, "can_cast": True, "contains_rune": rune}


def _extra(*items):
    payload = copy.deepcopy(gsi_match_stream(minutes=20, death_minutes=())[-1])
    payload["items"] = {f"slot{i}": item for i, item in enumerate(items)}
    return normalize_gsi_payload(payload)["extra_context"]


def test_the_rune_in_the_bottle_is_read_from_the_inventory_only():
    assert bottle_rune({"slot0": _bottle("haste")}) == "Haste"
    assert bottle_rune({"slot1": _bottle("regen")}) == "Regeneration"
    assert bottle_rune({"slot0": _bottle("empty")}) is None
    assert bottle_rune({"slot0": _bottle("")}) is None
    assert bottle_rune({"slot7": _bottle("haste")}) is None  # the backpack
    assert bottle_rune({"slot0": _bottle("something_new")}) is None
    assert bottle_rune(None) is None
    assert _extra(_bottle("invis"))["bottle_rune"] == "Invisibility"
    assert "bottle_rune" not in _extra(_bottle("empty"))


def test_a_bottle_with_a_power_rune_is_no_regen():
    # Pressed, it uses the rune, not a charge.
    assert regen_items({"slot0": _bottle("double_damage")}) == []
    assert regen_items({"slot0": _bottle("something_new")}) == []
    assert regen_items({"slot0": _bottle("regen", charges=0)}) == ["item_bottle"]
    assert regen_items({"slot0": _bottle("empty")}) == ["item_bottle"]
    assert regen_items({"slot0": _bottle("empty", charges=0)}) == []


def test_low_hp_with_an_escape_rune_in_the_bottle():
    action, reason = low_hp_copy(_extra(_bottle("haste")))
    assert action == "Use the Haste rune from your Bottle and run."
    assert (
        reason == "The Haste rune in your Bottle is ready: use it before the next hit, not after."
    )
    # An escape item still comes first.
    force = {"name": "item_force_staff", "can_cast": True, "cooldown": 0}
    action, _ = low_hp_copy(_extra(_bottle("haste"), force))
    assert action == "Use Force Staff now to get out, then reset HP."
    # Double Damage gets nobody out, and the Bottle is no heal with it inside.
    assert low_hp_copy(_extra(_bottle("double_damage"))) is None


def test_low_hp_with_a_regeneration_or_water_rune():
    action, reason = low_hp_copy(_extra(_bottle("regen", charges=0)))
    assert action == "Step out of enemy range and use the Regeneration rune from your Bottle."
    assert reason.startswith("The Regeneration rune heals fast but stops at the first hit")
    action, reason = low_hp_copy(_extra(_bottle("water", charges=0)))
    assert action == "Use the Water rune from your Bottle now, then step back."
    # An empty Bottle with charges keeps the plain over-time text.
    action, _ = low_hp_copy(_extra(_bottle("empty")))
    assert action == "Step out of enemy range and use Bottle."


def test_the_rune_texts_have_russian_and_keep_their_reason():
    texts = [
        "Use the Haste rune from your Bottle and run.",
        "The Haste rune in your Bottle is ready: use it before the next hit, not after.",
        "Use the Invisibility rune from your Bottle and run.",
        "Use the Water rune from your Bottle now, then step back.",
        "The Water rune in your Bottle heals you at once.",
        "Step out of enemy range and use the Regeneration rune from your Bottle.",
        "The Regeneration rune heals fast but stops at the first hit: "
        "use it where enemies cannot reach you.",
    ]
    for text in texts:
        russian = translate_ru(text)
        assert russian and "Bottle" not in russian and "rune" not in russian, text
    assert translate_ru(texts[0]) == "Используйте руну ускорения из бутылки и уходите."
    for reason in (texts[1], texts[4], texts[6]):
        assert clean_reason_text(reason, "LOW_HP") == reason


def test_the_live_card_names_the_bottled_haste(client):
    payload = copy.deepcopy(gsi_match_stream(minutes=20, death_minutes=())[-1])
    payload["hero"]["health_percent"] = 12
    payload["hero"]["health"] = 200
    payload["items"] = {"slot0": _bottle("haste")}
    client.post("/gsi", json=payload)
    body = client.get("/overlay/recommendation?lang=ru").json()
    assert body["recommendation"]["action"] == "Используйте руну ускорения из бутылки и уходите."


def _hint(tips, clock, rune, lang="en", alive=True):
    # Clocks between the timers (10:10-11:35, 12:10-13:35): the tip shows alone.
    return map_hint(
        clock, "mid", tips, alive=alive, has_ward=None, lang=lang, level=7, bottle_rune=rune
    )


def test_a_power_rune_kept_in_the_bottle_is_a_kill_to_make():
    tips = RoleTips()
    start = 10 * 60 + 10
    assert _hint(tips, start, "Haste") is None
    assert _hint(tips, start + BOTTLE_RUNE_HELD - 1, "Haste") is None
    tip = _hint(tips, start + BOTTLE_RUNE_HELD, "Haste")
    assert tip["title"] == "Haste rune in your Bottle"
    assert tip["id"] == f"bottle_rune@{start}"
    # Shown for a while, then once per rune.
    assert _hint(tips, start + BOTTLE_RUNE_HELD + BOTTLE_RUNE_SHOW, "Haste") is not None
    assert _hint(tips, start + BOTTLE_RUNE_HELD + BOTTLE_RUNE_SHOW + 1, "Haste") is None
    # Used, then a new rune bottled: counted again from then.
    assert _hint(tips, 680, None) is None
    assert _hint(tips, 735, "Arcane") is None
    again = _hint(tips, 735 + BOTTLE_RUNE_HELD, "Arcane", lang="ru")
    assert again["title"] == "Руна волшебства в бутылке"


def test_no_kill_tip_for_a_regeneration_rune_or_a_dead_hero():
    tips = RoleTips()
    assert _hint(tips, 610, "Regeneration") is None
    assert _hint(tips, 610 + BOTTLE_RUNE_HELD, "Regeneration") is None
    dead = RoleTips()
    assert _hint(dead, 610, "Haste", alive=False) is None
    assert _hint(dead, 610 + BOTTLE_RUNE_HELD, "Haste", alive=False) is None


def test_the_census_counts_the_bottled_rune_names():
    payload = copy.deepcopy(gsi_match_stream(minutes=20, death_minutes=())[-1])
    payload["map"]["game_state"] = "DOTA_GAMERULES_STATE_GAME_IN_PROGRESS"
    payload["items"] = {"slot0": _bottle("haste"), "slot1": {"name": "item_tango"}}
    census = GsiCensus()
    census.observe(payload)
    assert census.summary()["bottle_runes"] == {"haste": 1}
