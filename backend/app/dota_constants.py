"""
dota_constants.py - static Dota 2 reference data shared by the backend.

Hero ids and internal names follow the OpenDota / Valve API
(`/api/heroes`: id, localized_name, name). The table is static so match
reviews work offline; unknown ids fall back to "Hero <id>".
"""

from __future__ import annotations

from typing import Any

# hero_id -> (localized name, internal npc name)
HEROES: dict[int, tuple[str, str]] = {
    1: ("Anti-Mage", "npc_dota_hero_antimage"),
    2: ("Axe", "npc_dota_hero_axe"),
    3: ("Bane", "npc_dota_hero_bane"),
    4: ("Bloodseeker", "npc_dota_hero_bloodseeker"),
    5: ("Crystal Maiden", "npc_dota_hero_crystal_maiden"),
    6: ("Drow Ranger", "npc_dota_hero_drow_ranger"),
    7: ("Earthshaker", "npc_dota_hero_earthshaker"),
    8: ("Juggernaut", "npc_dota_hero_juggernaut"),
    9: ("Mirana", "npc_dota_hero_mirana"),
    10: ("Morphling", "npc_dota_hero_morphling"),
    11: ("Shadow Fiend", "npc_dota_hero_nevermore"),
    12: ("Phantom Lancer", "npc_dota_hero_phantom_lancer"),
    13: ("Puck", "npc_dota_hero_puck"),
    14: ("Pudge", "npc_dota_hero_pudge"),
    15: ("Razor", "npc_dota_hero_razor"),
    16: ("Sand King", "npc_dota_hero_sand_king"),
    17: ("Storm Spirit", "npc_dota_hero_storm_spirit"),
    18: ("Sven", "npc_dota_hero_sven"),
    19: ("Tiny", "npc_dota_hero_tiny"),
    20: ("Vengeful Spirit", "npc_dota_hero_vengefulspirit"),
    21: ("Windranger", "npc_dota_hero_windrunner"),
    22: ("Zeus", "npc_dota_hero_zuus"),
    23: ("Kunkka", "npc_dota_hero_kunkka"),
    25: ("Lina", "npc_dota_hero_lina"),
    26: ("Lion", "npc_dota_hero_lion"),
    27: ("Shadow Shaman", "npc_dota_hero_shadow_shaman"),
    28: ("Slardar", "npc_dota_hero_slardar"),
    29: ("Tidehunter", "npc_dota_hero_tidehunter"),
    30: ("Witch Doctor", "npc_dota_hero_witch_doctor"),
    31: ("Lich", "npc_dota_hero_lich"),
    32: ("Riki", "npc_dota_hero_riki"),
    33: ("Enigma", "npc_dota_hero_enigma"),
    34: ("Tinker", "npc_dota_hero_tinker"),
    35: ("Sniper", "npc_dota_hero_sniper"),
    36: ("Necrophos", "npc_dota_hero_necrolyte"),
    37: ("Warlock", "npc_dota_hero_warlock"),
    38: ("Beastmaster", "npc_dota_hero_beastmaster"),
    39: ("Queen of Pain", "npc_dota_hero_queenofpain"),
    40: ("Venomancer", "npc_dota_hero_venomancer"),
    41: ("Faceless Void", "npc_dota_hero_faceless_void"),
    42: ("Wraith King", "npc_dota_hero_skeleton_king"),
    43: ("Death Prophet", "npc_dota_hero_death_prophet"),
    44: ("Phantom Assassin", "npc_dota_hero_phantom_assassin"),
    45: ("Pugna", "npc_dota_hero_pugna"),
    46: ("Templar Assassin", "npc_dota_hero_templar_assassin"),
    47: ("Viper", "npc_dota_hero_viper"),
    48: ("Luna", "npc_dota_hero_luna"),
    49: ("Dragon Knight", "npc_dota_hero_dragon_knight"),
    50: ("Dazzle", "npc_dota_hero_dazzle"),
    51: ("Clockwerk", "npc_dota_hero_rattletrap"),
    52: ("Leshrac", "npc_dota_hero_leshrac"),
    53: ("Nature's Prophet", "npc_dota_hero_furion"),
    54: ("Lifestealer", "npc_dota_hero_life_stealer"),
    55: ("Dark Seer", "npc_dota_hero_dark_seer"),
    56: ("Clinkz", "npc_dota_hero_clinkz"),
    57: ("Omniknight", "npc_dota_hero_omniknight"),
    58: ("Enchantress", "npc_dota_hero_enchantress"),
    59: ("Huskar", "npc_dota_hero_huskar"),
    60: ("Night Stalker", "npc_dota_hero_night_stalker"),
    61: ("Broodmother", "npc_dota_hero_broodmother"),
    62: ("Bounty Hunter", "npc_dota_hero_bounty_hunter"),
    63: ("Weaver", "npc_dota_hero_weaver"),
    64: ("Jakiro", "npc_dota_hero_jakiro"),
    65: ("Batrider", "npc_dota_hero_batrider"),
    66: ("Chen", "npc_dota_hero_chen"),
    67: ("Spectre", "npc_dota_hero_spectre"),
    68: ("Ancient Apparition", "npc_dota_hero_ancient_apparition"),
    69: ("Doom", "npc_dota_hero_doom_bringer"),
    70: ("Ursa", "npc_dota_hero_ursa"),
    71: ("Spirit Breaker", "npc_dota_hero_spirit_breaker"),
    72: ("Gyrocopter", "npc_dota_hero_gyrocopter"),
    73: ("Alchemist", "npc_dota_hero_alchemist"),
    74: ("Invoker", "npc_dota_hero_invoker"),
    75: ("Silencer", "npc_dota_hero_silencer"),
    76: ("Outworld Destroyer", "npc_dota_hero_obsidian_destroyer"),
    77: ("Lycan", "npc_dota_hero_lycan"),
    78: ("Brewmaster", "npc_dota_hero_brewmaster"),
    79: ("Shadow Demon", "npc_dota_hero_shadow_demon"),
    80: ("Lone Druid", "npc_dota_hero_lone_druid"),
    81: ("Chaos Knight", "npc_dota_hero_chaos_knight"),
    82: ("Meepo", "npc_dota_hero_meepo"),
    83: ("Treant Protector", "npc_dota_hero_treant"),
    84: ("Ogre Magi", "npc_dota_hero_ogre_magi"),
    85: ("Undying", "npc_dota_hero_undying"),
    86: ("Rubick", "npc_dota_hero_rubick"),
    87: ("Disruptor", "npc_dota_hero_disruptor"),
    88: ("Nyx Assassin", "npc_dota_hero_nyx_assassin"),
    89: ("Naga Siren", "npc_dota_hero_naga_siren"),
    90: ("Keeper of the Light", "npc_dota_hero_keeper_of_the_light"),
    91: ("Io", "npc_dota_hero_wisp"),
    92: ("Visage", "npc_dota_hero_visage"),
    93: ("Slark", "npc_dota_hero_slark"),
    94: ("Medusa", "npc_dota_hero_medusa"),
    95: ("Troll Warlord", "npc_dota_hero_troll_warlord"),
    96: ("Centaur Warrunner", "npc_dota_hero_centaur"),
    97: ("Magnus", "npc_dota_hero_magnataur"),
    98: ("Timbersaw", "npc_dota_hero_shredder"),
    99: ("Bristleback", "npc_dota_hero_bristleback"),
    100: ("Tusk", "npc_dota_hero_tusk"),
    101: ("Skywrath Mage", "npc_dota_hero_skywrath_mage"),
    102: ("Abaddon", "npc_dota_hero_abaddon"),
    103: ("Elder Titan", "npc_dota_hero_elder_titan"),
    104: ("Legion Commander", "npc_dota_hero_legion_commander"),
    105: ("Techies", "npc_dota_hero_techies"),
    106: ("Ember Spirit", "npc_dota_hero_ember_spirit"),
    107: ("Earth Spirit", "npc_dota_hero_earth_spirit"),
    108: ("Underlord", "npc_dota_hero_abyssal_underlord"),
    109: ("Terrorblade", "npc_dota_hero_terrorblade"),
    110: ("Phoenix", "npc_dota_hero_phoenix"),
    111: ("Oracle", "npc_dota_hero_oracle"),
    112: ("Winter Wyvern", "npc_dota_hero_winter_wyvern"),
    113: ("Arc Warden", "npc_dota_hero_arc_warden"),
    114: ("Monkey King", "npc_dota_hero_monkey_king"),
    119: ("Dark Willow", "npc_dota_hero_dark_willow"),
    120: ("Pangolier", "npc_dota_hero_pangolier"),
    121: ("Grimstroke", "npc_dota_hero_grimstroke"),
    123: ("Hoodwink", "npc_dota_hero_hoodwink"),
    126: ("Void Spirit", "npc_dota_hero_void_spirit"),
    128: ("Snapfire", "npc_dota_hero_snapfire"),
    129: ("Mars", "npc_dota_hero_mars"),
    131: ("Ringmaster", "npc_dota_hero_ringmaster"),
    135: ("Dawnbreaker", "npc_dota_hero_dawnbreaker"),
    136: ("Marci", "npc_dota_hero_marci"),
    137: ("Primal Beast", "npc_dota_hero_primal_beast"),
    138: ("Muerta", "npc_dota_hero_muerta"),
    145: ("Kez", "npc_dota_hero_kez"),
}

HERO_ID_TO_NAME: dict[int, str] = {hero_id: names[0] for hero_id, names in HEROES.items()}
NPC_TO_HERO_ID: dict[str, int] = {names[1]: hero_id for hero_id, names in HEROES.items()}
_NAME_TO_HERO_ID: dict[str, int] = {names[0].lower(): hero_id for hero_id, names in HEROES.items()}


def hero_name(hero_id: Any) -> str:
    try:
        key = int(hero_id)
    except (TypeError, ValueError):
        return "Unknown"
    return HERO_ID_TO_NAME.get(key, f"Hero {key}")


def hero_npc_name(hero_id: Any) -> str:
    try:
        return HEROES[int(hero_id)][1]
    except (KeyError, TypeError, ValueError):
        return ""


def hero_id_from_name(name: object) -> int | None:
    """Localized ("Anti-Mage") or internal ("npc_dota_hero_antimage") name -> id."""
    text = str(name or "").strip()
    if not text:
        return None
    if text.startswith("npc_dota_hero_"):
        return NPC_TO_HERO_ID.get(text)
    return _NAME_TO_HERO_ID.get(text.lower())


def hero_name_from_npc(npc_name: object) -> str:
    hero_id = NPC_TO_HERO_ID.get(str(npc_name or ""))
    return hero_name(hero_id) if hero_id is not None else str(npc_name or "")


# OpenDota lane_role: 1 safe lane, 2 mid, 3 off lane, 4 jungle.
LANE_ROLES = {1: "safe", 2: "mid", 3: "off", 4: "jungle"}

# OpenDota lobby_type values worth reviewing: normal 0, tournament 2, team/solo
# ranked 5/6, ranked 7, Battle Cup 9. Practice 1, co-op bots 4 and 1v1 mid 8
# are skipped.
REVIEWABLE_LOBBY_TYPES = {0, 2, 5, 6, 7, 9}
