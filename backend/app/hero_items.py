"""
hero_items.py - counter items for the player's own hero (data/heroes/item_plans).

situational_items answers an enemy hero by kind and position alone: a carry
against evasion gets Monkey King Bar, whoever the carry is. A hero's plan says
what that hero buys instead, from the hero's build and the items' current
mechanics (each rule keeps its `basis`), e.g. Terrorblade:

- evasion (Phantom Assassin, Windranger) and an escape a silence stops (Queen
  of Pain's Blink, Storm Spirit's Ball Lightning...): Bloodthorn — the silence
  stops the escape and gives True Strike to his illusions too;
- evasion alone: Monkey King Bar;
- heavy healing: his own Eye of Skadi after Manta Style;
- illusion heroes: Butterfly, and the Dragon Lance into Hydra's Breath
  (Metamorphosis attacks from range) instead of Hurricane Pike;
- heroes who jump on him (Slark, Phantom Assassin, Spirit Breaker): Pike.

`build`: the hero's usual order when no counter or tempo holds (high-rank
won games, instead of the all-ranks OpenDota popularity); `unless` skips an
entry another item answered (Hurricane Pike after Hydra's Breath).

`tempo`: with the player's own net worth over the plan's curve (minute → net
worth, from high-rank games where the hero wins ~85% above it) the counters
wait and the next item is the tempo build's (Terrorblade, in the order of his
farmed won games: Manta Style, Aghanim's Shard, Dragon Lance, Eye of Skadi,
Butterfly, Daedalus), then the Aegis and the throne. A player's GSI
shows no enemy net worth, so the hero's own farm is the observed sign.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.config import DATA_DIR

ITEM_PLANS_DIR = DATA_DIR / "heroes" / "item_plans"
SCHEMA = 1
# Every why a rule may use has a reason in each place that shows one:
# map_hints.TIPS (draft_<why>), death_screen.TEXT (why_<why>) and
# post_laning_coach.SITUATIONAL_BECAUSE (tests/test_hero_items.py checks it).
WHYS = {
    "evasion",
    "evasion_escape",
    "healing",
    "illusions",
    "illusion_evasion",
    "illusion_splash",
    "jumper",
    "break",
    "magic",
}
# The tempo build's why: shown on the death screen and in the farm advice.
TEMPO_WHY = "tempo"
POSITIONS = {"carry", "mid", "offlane"}
RULE_KEYS = {"id", "why", "family", "item", "name", "enemy", "also", "minute", "basis"}


def groups() -> dict[str, dict[str, str | None]]:
    """Enemy hero groups a rule names: {group: {hero: spell or None}}."""
    from app.draft_analysis import COUNTERS, ESCAPES, JUMPERS
    from app.situational_items import BREAK_PASSIVES

    return {
        "evasion": dict.fromkeys(COUNTERS["evasion"][0]),
        "illusions": dict.fromkeys(COUNTERS["illusions"][0]),
        "healing": dict.fromkeys(COUNTERS["healing"][0]),
        "escape": dict(ESCAPES),
        "break": dict(BREAK_PASSIVES),
        "jumpers": dict(JUMPERS),
    }


def validate(plan: Any, source: str = "plan") -> dict[str, Any]:
    """The plan when it follows the schema; ValueError naming what is wrong."""
    from app.dota_constants import hero_id_from_name

    def fail(message: str) -> ValueError:
        return ValueError(f"{source}: {message}")

    if not isinstance(plan, dict) or plan.get("schema") != SCHEMA:
        raise fail(f"schema must be {SCHEMA}")
    if hero_id_from_name(plan.get("hero")) is None:
        raise fail(f"unknown hero {plan.get('hero')!r}")
    positions = plan.get("positions")
    if not isinstance(positions, list) or not positions or not set(positions) <= POSITIONS:
        raise fail(f"positions must be some of {sorted(POSITIONS)}")
    known = groups()
    rules = plan.get("rules")
    if not isinstance(rules, list) or not rules:
        raise fail("no rules")
    ids: set[str] = set()
    for rule in rules:
        if not isinstance(rule, dict) or not set(rule) <= RULE_KEYS:
            raise fail(f"a rule has unknown keys: {sorted(set(rule) - RULE_KEYS)}")
        rule_id = rule.get("id")
        if not isinstance(rule_id, str) or rule_id in ids:
            raise fail(f"rule id {rule_id!r} is missing or repeated")
        ids.add(rule_id)
        if rule.get("why") not in WHYS:
            raise fail(f"{rule_id}: why must be one of {sorted(WHYS)}")
        for key in ("family", "item", "name", "basis"):
            if not isinstance(rule.get(key), str) or not rule[key].strip():
                raise fail(f"{rule_id}: {key} is required")
        for key in ("enemy", "also"):
            if key in rule and rule[key] not in known:
                raise fail(f"{rule_id}: {key} must be one of {sorted(known)}")
        if "enemy" not in rule:
            raise fail(f"{rule_id}: enemy is required")
        minute = rule.get("minute")
        if isinstance(minute, bool) or not isinstance(minute, int) or not 0 <= minute <= 60:
            raise fail(f"{rule_id}: minute must be 0..60")
    suppress = plan.get("suppress", {})
    if not isinstance(suppress, dict) or not all(
        isinstance(v, str) and v.strip() for v in suppress.values()
    ):
        raise fail("suppress maps a generic why to the reason it does not fit")
    build = plan.get("build")
    if build is not None and (
        not isinstance(build, list)
        or not build
        or not all(
            isinstance(e, dict)
            and isinstance(e.get("item"), str)
            and e.get("name")
            and all(isinstance(u, str) for u in e.get("unless", []))
            for e in build
        )
        or not isinstance(plan.get("build_basis"), str)
        or not plan["build_basis"].strip()
    ):
        raise fail("build needs items [{item, name, unless?}] and a build_basis")
    tempo = plan.get("tempo")
    if tempo is not None:
        items = tempo.get("items") if isinstance(tempo, dict) else None
        raw = tempo.get("net_worth") if isinstance(tempo, dict) else None
        curve: list[Any] = raw if isinstance(raw, list) else []
        points = [p for p in curve if isinstance(p, list) and len(p) == 2]
        if (
            not isinstance(items, list)
            or not items
            or not all(
                isinstance(i, dict) and isinstance(i.get("item"), str) and i.get("name")
                for i in items
            )
            or not points
            or len(points) != len(curve)
            or not all(
                all(isinstance(v, int) and not isinstance(v, bool) and v > 0 for v in p)
                for p in points
            )
            or [p[0] for p in points] != sorted({p[0] for p in points})
            or not isinstance(tempo.get("basis"), str)
            or not tempo["basis"].strip()
        ):
            raise fail(
                "tempo needs items [{item, name}], a net_worth curve [[minute, gold], ...] "
                "with rising minutes, and a basis"
            )
    return plan


@lru_cache(maxsize=1)
def load_plans(directory: Path = ITEM_PLANS_DIR) -> dict[int, dict[str, Any]]:
    """{hero id: plan} for every plan file; a broken file raises (tests and CI
    load them all)."""
    from app.dota_constants import hero_id_from_name

    plans: dict[int, dict[str, Any]] = {}
    for path in sorted(directory.glob("*.json")):
        plan = validate(json.loads(path.read_text(encoding="utf-8")), path.name)
        hero_id = hero_id_from_name(plan["hero"])
        if hero_id is None or hero_id in plans:
            raise ValueError(f"{path.name}: a second plan for {plan['hero']}")
        plans[hero_id] = plan
    return plans


def plan_for(hero: Any, position: str | None) -> dict[str, Any] | None:
    """The hero's plan when the hero plays one of its positions; else None."""
    from app.dota_constants import hero_id_from_name

    hero_id = hero_id_from_name(hero) if isinstance(hero, str) else None
    plan = load_plans().get(hero_id) if hero_id is not None else None
    if plan is None or position not in plan["positions"]:
        return None
    return plan


def replaced(plan: dict[str, Any]) -> set[str]:
    """The generic whys the plan answers itself or drops."""
    return {rule["family"] for rule in plan["rules"]} | set(plan.get("suppress", {}))


def hero_rows(plan: dict[str, Any], enemies: list[str], minute: int | None) -> list[dict[str, Any]]:
    """The plan's rules that hold, first per family: {why, key, name, enemy,
    escape, spell, family_items}."""
    known = groups()
    family_items: dict[str, list[str]] = {}
    for rule in plan["rules"]:
        family_items.setdefault(rule["family"], []).append(rule["item"])
    rows: list[dict[str, Any]] = []
    done: set[str] = set()
    for rule in plan["rules"]:
        if rule["family"] in done or (minute or 0) < rule["minute"]:
            continue
        enemy = next((e for e in enemies if e in known[rule["enemy"]]), None)
        if enemy is None:
            continue
        escape = None
        if "also" in rule:
            escape = next((e for e in enemies if e in known[rule["also"]] and e != enemy), None)
            if escape is None:
                continue
        spell = known[rule["also"]].get(escape) if escape else known[rule["enemy"]].get(enemy)
        done.add(rule["family"])
        rows.append(
            {
                "why": rule["why"],
                "key": rule["item"],
                "name": rule["name"],
                "enemy": enemy,
                "escape": escape,
                "spell": spell,
                "family_items": family_items[rule["family"]],
            }
        )
    return rows


def tempo_threshold(plan: dict[str, Any], minute: int | None) -> int | None:
    """The plan's tempo net worth for `minute`: linear between the curve's
    points, the last segment's slope after them; None before the first point."""
    tempo = plan.get("tempo")
    if not tempo or not isinstance(minute, int):
        return None
    points = tempo["net_worth"]
    if minute < points[0][0]:
        return None
    for (m0, g0), (m1, g1) in zip(points, points[1:], strict=False):
        if m0 <= minute <= m1:
            return round(g0 + (g1 - g0) * (minute - m0) / (m1 - m0))
    if len(points) == 1:
        return points[0][1]
    (m0, g0), (m1, g1) = points[-2], points[-1]
    return round(g1 + (g1 - g0) * (minute - m1) / (m1 - m0))


def tempo_rows(
    plan: dict[str, Any], net_worth: int | None, minute: int | None
) -> list[dict[str, Any]] | None:
    """The tempo build's items in order when the player's net worth is over the
    plan's curve ({key, name}); None otherwise (the counters stay)."""
    threshold = tempo_threshold(plan, minute)
    if threshold is None or not isinstance(net_worth, int) or net_worth < threshold:
        return None
    return [{"key": i["item"], "name": i["name"]} for i in plan["tempo"]["items"]]
