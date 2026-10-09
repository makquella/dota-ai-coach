"""One hero identity: app/dota_constants.py HEROES is the canonical id -> (name,
npc) table; every other place that names heroes (the launcher's generated
dota-data.js, hero profiles and safety rules, STRATZ builds, the supported
list, live GSI names, share portrait keys) must resolve to it."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from app.dota_constants import (
    HEROES,
    NPC_TO_HERO_ID,
    _fold_hero,
    hero_id_from_any,
    hero_id_from_name,
    hero_key,
    hero_name_from_npc,
)
from app.gsi_state import _normalize_hero_name
from app.schemas import SUPPORTED_HEROES, hero_coverage, safety_only_hero
from app.share_review import _hero_key as share_hero_key

REPO = Path(__file__).resolve().parents[2]


def _json(path: str) -> dict:
    return json.loads((REPO / path).read_text(encoding="utf-8"))


def test_names_npc_names_and_folded_spellings_are_unique():
    names = [name for name, _ in HEROES.values()]
    npcs = [npc for _, npc in HEROES.values()]
    assert len(set(names)) == len(names)
    assert len(set(npcs)) == len(npcs)
    assert all(npc.startswith("npc_dota_hero_") for npc in npcs)
    owner: dict[str, int] = {}
    for hero_id, (name, npc) in HEROES.items():
        for folded in {_fold_hero(name), _fold_hero(npc)}:
            assert owner.setdefault(folded, hero_id) == hero_id, (folded, hero_id)


@pytest.mark.parametrize("hero_id", sorted(HEROES))
def test_every_hero_round_trips_through_each_spelling(hero_id):
    name, npc = HEROES[hero_id]
    key = npc.removeprefix("npc_dota_hero_")
    assert hero_id_from_name(name) == hero_id
    assert NPC_TO_HERO_ID[npc] == hero_id
    assert hero_name_from_npc(npc) == name
    assert hero_key(hero_id) == key == share_hero_key(hero_id)
    # Live GSI sends the npc name; old builds title-cased unknown keys.
    for spelling in (name, npc, key, key.replace("_", " ").title(), name.upper()):
        assert hero_id_from_any(spelling) == hero_id, spelling
        assert _normalize_hero_name(spelling) == name, spelling
    assert hero_coverage(name) is not None
    assert hero_coverage(npc) is not None


def test_spellings_whose_npc_key_differs_from_the_name():
    assert hero_id_from_any("Nevermore") == hero_id_from_any("Shadow Fiend")
    assert safety_only_hero("Furion") == "Nature's Prophet"
    assert safety_only_hero("npc_dota_hero_obsidian_destroyer") is None  # profiled: OD
    assert _normalize_hero_name("npc_dota_hero_life_stealer") == "Lifestealer"
    assert _normalize_hero_name("npc_dota_hero_brand_new") == "Brand New"
    assert hero_id_from_any("") is None
    assert hero_id_from_any("not a hero") is None
    assert hero_key(None) is None
    assert hero_key(99999) is None


def test_launcher_dota_data_is_generated_from_heroes():
    text = (REPO / "frontend/launcher/renderer/dota-data.js").read_text(encoding="utf-8")
    data = json.loads(re.search(r"window\.DotaData = (\{.*\});", text, re.S).group(1))
    expected = {
        str(i): [name, npc.removeprefix("npc_dota_hero_")] for i, (name, npc) in HEROES.items()
    }
    assert data["heroes"] == expected, "run backend/scripts/build_dota_data.py"


def test_supported_profiled_and_rule_heroes_are_canonical_names():
    canonical = {name for name, _ in HEROES.values()}
    assert set(SUPPORTED_HEROES) <= canonical
    profiles = _json("data/heroes/hero_profiles.json")["profiles"]
    for profile in profiles:
        hero = profile["hero"]
        assert hero in canonical, hero
        for alias in profile.get("aliases", []):
            assert hero_id_from_any(alias) in (None, hero_id_from_name(hero)), (hero, alias)
    assert set(_json("data/heroes/hero_safety_rules.json")["heroes"]) <= canonical


def test_stratz_builds_use_known_hero_ids():
    builds = _json("data/meta/stratz_builds.json")["heroes"]
    unknown = sorted(int(hero_id) for hero_id in builds if int(hero_id) not in HEROES)
    assert unknown == []
