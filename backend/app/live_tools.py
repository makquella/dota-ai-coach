"""
live_tools.py - what the player can press right now, for the survival advice.

The survival cards ("Leave the wave and reset HP", "Wait out the disable",
"After respawn, change your route") were the same every time. With the live
GSI items they can name the tool that is ready:

- low HP: an escape (Force Staff, Eul's, Ghost Scepter…), an instant heal
  (Magic Wand with its charges, Satanic, Faerie Fire…) or regen to use out of
  sight (Healing Salve, Tango, Bottle);
- a disable: what dispels it or gets out once it ends (Black King Bar, Manta
  Style, Lotus Orb…); a silence alone does not stop items, so then "now";
- a death: the rescue item that was ready and not pressed in the last seconds
  (last_moments.py, from the match recording).

Only what GSI reports as ready counts (last_moments.ready_savers: castable, off
cooldown, a Magic Wand from 10 charges); without an items block nothing is
claimed and the plain text stays.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.hero_profiles import find_ability, get_key_safety_abilities
from app.last_moments import ABILITY_PREFIX, SAVERS, saver_label

# Low HP: first a way out, then an instant heal.
ESCAPES = (
    "item_force_staff",
    "item_hurricane_pike",
    "item_cyclone",
    "item_wind_waker",
    "item_ghost",
    "item_glimmer_cape",
    "item_invis_sword",
    "item_silver_edge",
    "item_manta",
    "item_blink",
    "item_swift_blink",
    "item_arcane_blink",
    "item_overwhelming_blink",
    "item_black_king_bar",
)
# Only real instant heals: Satanic and Bloodstone heal through lifesteal while
# attacking or casting, so "press it and step back" would heal nothing.
INSTANT_HEALS = (
    "item_magic_wand",
    "item_guardian_greaves",
)
# Consumables that heal: instant first, then over time (use out of sight).
REGEN_INSTANT = {"item_faerie_fire": "Faerie Fire", "item_cheese": "Cheese"}
REGEN_OVER_TIME = {
    "item_flask": "Healing Salve",
    "item_bottle": "Bottle",
    "item_tango": "Tango",
    "item_tango_single": "Tango",
}
# A disable: what removes it or gets out the moment it ends.
DISPELS = (
    "item_black_king_bar",
    "item_manta",
    "item_lotus_orb",
    "item_cyclone",
    "item_wind_waker",
    "item_satanic",
    "item_guardian_greaves",
    "item_disperser",
)

# Profile abilities that can be pressed as a save right now: no target needed
# (or a point / self cast) and not passive. Target-dependent skills (Sunder,
# Phantom Strike, Tree Dance, Fire Remnant), passives (Dispersion, Mana Shield)
# and toggles (Attribute Shift) never count, in live advice or as "unpressed".
USABLE_SAFETY = {
    "blink",
    "blade fury",
    "rage",
    "shadow dance",
    "dark pact",
    "pounce",
    "waveform",
    "blur",
    "gust",
    "warcry",
    "grappling claw",
    "raptor dance",
    "enrage",
    "mischief",
    "doppelganger",
    "mirror image",
    "song of the siren",
    "concussive grenade",
    "pierce the veil",
    "flame guard",
    "sleight of fist",
    # Mid and offlane cores.
    "ball lightning",
    "phase shift",
    "refraction",
    "dissimilate",
    "stampede",
    "guardian sprint",
    "timber chain",
    "swashbuckle",
    # Supports: escapes and saves on self (Shallow Grave, False Promise, Frost
    # Shield and Living Armor can be cast on yourself).
    "leap",
    "scurry",
    "bulldoze",
    "vendetta",
    "spiked carapace",
    "shadow walk",
    "rolling boulder",
    "firesnap cookie",
    "shallow grave",
    "false promise",
    "frost shield",
    "living armor",
}

LOW_HP_ACTION_TYPES = {
    "retreat_reset",
    "play_back_and_regen",
    "stop_overstay_low_hp",
    "stabilize_after_recent_damage",
}


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _count(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value != value:
        return 0
    return int(value) if 0 <= value < 1000 else 0


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value != value:
        return None
    return float(value)


def hero_tools(hero: Any, abilities: Any) -> dict[str, Any]:
    """The hero's own escape and defensive abilities (hero_profiles.json) from the
    live GSI abilities: `ready` [(name, kind)] — learned, off cooldown and not
    marked uncastable — escapes first, and `cooldowns` {name: seconds left}."""
    ready: list[tuple[str, str]] = []
    cooldowns: dict[str, int] = {}
    if not isinstance(hero, str) or not hero or not isinstance(abilities, list):
        return {"ready": ready, "cooldowns": cooldowns}
    key = get_key_safety_abilities(hero)
    for kind in ("escape", "defensive"):
        for name in key[kind]:
            if name.lower() not in USABLE_SAFETY:
                continue
            ability = find_ability(abilities, name)
            if not ability or not (_number(ability.get("level")) or 0) > 0:
                continue
            cooldown = _number(ability.get("cooldown"))
            if cooldown is not None and cooldown > 0:
                cooldowns[name] = int(-(-cooldown // 1))
            elif ability.get("can_cast") is not False and cooldown is not None:
                ready.append((name, kind))
    return {"ready": ready, "cooldowns": cooldowns}


def ready_abilities(hero: Any, abilities: Any) -> list[str]:
    """Names of the hero's safety abilities that could be pressed now."""
    return [name for name, _ in hero_tools(hero, abilities)["ready"]]


def regen_items(items: Any) -> list[str] | None:
    """Healing consumables in the inventory that can be used (None: no items block)."""
    if not isinstance(items, dict) or not items:
        return None
    found: list[str] = []
    for slot, value in items.items():
        item = _dict(value)
        name = item.get("name")
        if not str(slot).startswith("slot") or not isinstance(name, str) or name in found:
            continue
        if name not in REGEN_INSTANT and name not in REGEN_OVER_TIME:
            continue
        if item.get("can_cast") is False:
            continue
        if name == "item_bottle" and _count(item.get("charges")) < 1:
            continue
        found.append(name)
    return found


def wand_charges(items: Any) -> int | None:
    for slot, value in _dict(items).items():
        item = _dict(value)
        if str(slot).startswith("slot") and item.get("name") == "item_magic_wand":
            return _count(item.get("charges"))
    return None


def _label(name: str) -> str:
    if name.startswith(ABILITY_PREFIX) or name in SAVERS:
        return saver_label(name, "en")
    return REGEN_INSTANT.get(name) or REGEN_OVER_TIME.get(name) or name


def _first(ready: list[str], order: tuple[str, ...]) -> str | None:
    return next((name for name in order if name in ready), None)


def _ready(extra: Mapping[str, Any]) -> list[str] | None:
    ready = extra.get("ready_savers")
    if not isinstance(ready, list):
        return None
    return [name for name in ready if isinstance(name, str)]


def _items_blocked(extra: Mapping[str, Any]) -> bool:
    """Stunned, hexed or muted: no item can be used right now."""
    return any(extra.get(flag) is True for flag in ("stunned", "hexed", "muted"))


def _abilities_blocked(extra: Mapping[str, Any]) -> bool:
    """Stunned, hexed or silenced: no ability can be cast (a mute stops items only)."""
    return any(extra.get(flag) is True for flag in ("stunned", "hexed", "silenced"))


def _own_ready(extra: Mapping[str, Any], hero: Any) -> list[tuple[str, str]]:
    if _abilities_blocked(extra):
        return []
    return hero_tools(hero, extra.get("abilities"))["ready"]


LOW_HP_REPEAT_FROM = 2  # low-HP cards before this one


def low_hp_repeat_reason(extra: Mapping[str, Any]) -> str | None:
    """The reason of a low-HP card that has come before in this match: the same
    «use Blink now» a fifth time says nothing new, how often it happens does."""
    before = extra.get("low_hp_before")
    if not isinstance(before, int) or isinstance(before, bool) or before < LOW_HP_REPEAT_FROM:
        return None
    reason = (
        f"Your HP has dropped this low {before + 1} times this game: "
        "heal up fully before you go back."
    )
    regen = extra.get("regen_items")
    if isinstance(regen, list) and not regen:
        reason += " No regen in your bag: have the courier bring a Healing Salve."
    return reason


def low_hp_copy(extra: Mapping[str, Any], hero: Any = None) -> tuple[str, str] | None:
    """(action, reason) naming the tool to press at low HP; None without one.
    Stunned, hexed or muted, no item can be pressed: the post-disable wording."""
    if extra.get("stunned") is True or extra.get("hexed") is True:
        return disabled_copy(extra, hero)
    own = _own_ready(extra, hero)
    if own:
        name, kind = own[0]
        if kind == "escape":
            return (
                f"Use {name} now to get out, then reset HP.",
                f"Your HP is low and {name} is ready: use it before the next hit, not after.",
            )
        return (
            f"Use {name} now and walk out of the fight.",
            f"{name} is ready: it buys you the seconds to get away.",
        )
    if _items_blocked(extra):  # muted: the items wait until it ends
        return disabled_copy(extra, hero)
    # Items: only what the GSI items block shows (none → nothing claimed).
    ready = _ready(extra) or []
    escape = _first(ready, ESCAPES)
    if escape:
        name = _label(escape)
        return (
            f"Use {name} now to get out, then reset HP.",
            f"Your HP is low and {name} is ready: use it before the next hit, not after.",
        )
    heal = _first(ready, INSTANT_HEALS)
    if heal == "item_magic_wand":
        charges = _count(extra.get("wand_charges"))
        return (
            "Use Magic Wand now, then step back.",
            f"Magic Wand has {charges} charges: that HP is yours right now."
            if charges
            else "Magic Wand is charged: that HP is yours right now.",
        )
    if heal:
        name = _label(heal)
        return (f"Use {name} now, then step back.", f"{name} is ready and heals you at once.")
    regen = extra.get("regen_items")
    regen = [n for n in regen if isinstance(n, str)] if isinstance(regen, list) else []
    instant = next((n for n in regen if n in REGEN_INSTANT), None)
    if instant:
        name = _label(instant)
        return (f"Use {name} now, then step back.", f"{name} heals you at once.")
    over_time = next((n for n in regen if n in REGEN_OVER_TIME), None)
    if over_time:
        name = _label(over_time)
        return (
            f"Step out of enemy range and use {name}.",
            f"{name} heals over time: use it where enemies cannot hit you.",
        )
    return None


def disabled_copy(extra: Mapping[str, Any], hero: Any = None) -> tuple[str, str] | None:
    """(action, reason) for a disable when a dispel or escape is ready: a dispel
    item, then the hero's own escape or defensive ability, then an escape item."""
    ready = _ready(extra) or []
    blocked = _items_blocked(extra)
    tool = _first(ready, DISPELS)
    if not blocked and extra.get("silenced") is True and tool:
        name = _label(tool)
        return (
            f"Use {name} now: it removes the silence.",
            "A silence does not stop items: get rid of it before the next spell lands.",
        )
    own = [name for name, _ in _own_ready(extra, hero)]
    if (
        own
        and blocked
        and extra.get("muted") is True
        and not (extra.get("stunned") is True or extra.get("hexed") is True)
    ):
        # Muted only: items wait, the hero's spells do not.
        return (
            f"Use {own[0]} now: a mute blocks items, not spells.",
            f"{own[0]} is ready: it buys you the seconds to get away.",
        )
    if not own:
        own = [n for n, _ in hero_tools(hero, extra.get("abilities"))["ready"]]
    name = _label(tool) if tool else (own[0] if own else None)
    if name is None and _first(ready, ESCAPES):
        name = _label(_first(ready, ESCAPES) or "")
    if not blocked or not name:
        return None
    return (
        f"The moment the disable ends, use {name}.",
        f"{name} is ready: the second after a disable is when most kills finish.",
    )


ZONES = {"top": "top lane", "mid": "mid lane", "bot": "bottom lane", "jungle": "jungle"}
SIDES = {"own": "on your side", "river": "by the river", "enemy": "on the enemy side"}


def death_items_reason(extra: Mapping[str, Any]) -> str | None:
    """The rescue item that was ready and not pressed before the last death."""
    items = extra.get("death_items")
    if not isinstance(items, list):
        return None
    names = [
        _label(n)
        for n in items
        if isinstance(n, str) and (n in SAVERS or n.startswith(ABILITY_PREFIX))
    ]
    if not names:
        return None
    return f"You died with {names[0]} ready: next time use it at the first big hit."


def death_copy(extra: Mapping[str, Any], *, route: bool = True) -> tuple[str | None, str | None]:
    """(action, reason) of a death advice from where it happened and what was
    left unpressed; None for a part that stays as it is.

    Two or more deaths in the same zone and half within ten minutes → stay away
    from there; one death on the enemy half → farm your own half; the unpressed
    item is the lesson and wins the reason."""
    action = reason = None
    place = extra.get("death_place")
    if isinstance(place, Mapping) and place.get("zone") in ZONES and place.get("side") in SIDES:
        where = f"{ZONES[place['zone']]} {SIDES[place['side']]}"
        count = place.get("count") if isinstance(place.get("count"), int) else 1
        minutes = place.get("minutes") if isinstance(place.get("minutes"), int) else 1
        if count >= 2:
            action = f"After respawn, stay away from the {where}."
            noun = "minute" if minutes == 1 else "minutes"
            reason = (
                f"{count} deaths in the {where} in {minutes} {noun}: "
                "farm somewhere safer until your team is there."
            )
        elif place["side"] == "enemy":
            reason = (
                f"You died in the {ZONES[place['zone']]} on the enemy side: "
                "farm your own half until your team is with you."
            )
    # How many deaths: only in place of a route line (`route`), never over the
    # escape or resource advice.
    recent = extra.get("recent_deaths") if route else None
    if action is None and isinstance(recent, Mapping):
        # Deaths in different places (or no place known): how many, how fast.
        count, minutes = recent.get("count"), recent.get("minutes")
        if isinstance(count, int) and count >= 2 and isinstance(minutes, int) and minutes >= 1:
            action = (
                f"After respawn, change your route: {count} deaths in the last {minutes} "
                f"{'minute' if minutes == 1 else 'minutes'}."
            )
    total = extra.get("match_deaths") if route else None
    if action is None and isinstance(total, int) and total >= 2:
        # Spread over the game: the count still says this is a pattern.
        action = f"After respawn, change your route: {total} deaths this game."
    if action is None and route:
        action, reason = _single_death_copy(extra, place, reason)
    return action, death_items_reason(extra) or reason


LANES = ("top", "mid", "bot")
LANING_END = 600  # clock seconds: a lane death before this is a laning death


def _single_death_copy(
    extra: Mapping[str, Any], place: Any, reason: str | None
) -> tuple[str | None, str | None]:
    """The first death (or the only one lately): where it was, else how fast it
    came, in place of «plan a safer route»."""
    if isinstance(place, Mapping) and place.get("zone") in ZONES and place.get("side") in SIDES:
        zone, side = ZONES[place["zone"]], place["side"]
        if side == "enemy":
            # The lesson moves into the action; the reason is free for the
            # unpressed item or what to buy.
            return (
                f"After respawn, farm your own half: you died in the {zone} on the enemy side.",
                None,
            )
        clock = extra.get("clock_time")
        if place["zone"] in LANES and isinstance(clock, int) and 0 <= clock < LANING_END:
            return (
                f"After respawn, play the {zone} closer to your tower until you see the enemy heroes.",
                reason,
            )
        return (
            f"After respawn, avoid the {zone} {SIDES[side]} without your team: you died there.",
            reason,
        )
    burst = extra.get("death_burst")
    if isinstance(burst, int) and 1 <= burst <= 5:
        noun = "second" if burst == 1 else "seconds"
        return (
            f"After respawn, stay near your towers or your team: "
            f"you went down in {burst} {noun} from high HP.",
            reason,
        )
    return None, reason
