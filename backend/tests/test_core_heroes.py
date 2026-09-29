"""Mid and offlane cores in the full advisor (hero_profiles.json `position`)."""

from __future__ import annotations

import pytest
from test_live_tools import _ability, _extra

from app.gsi_state import _normalize_hero_name
from app.hero_profiles import get_hero_position, get_laning_thresholds, hero_aliases
from app.live_tools import USABLE_SAFETY, low_hp_copy
from app.player_api import PLAYER_SERVICE
from app.schemas import SUPPORTED_HEROES, hero_coverage

# Profile abilities that are not a no-target save (a unit target, a passive, a toggle).
NOT_A_SAVE = {
    "sunder",
    "phantom strike",
    "tree dance",
    "fire remnant",
    "dispersion",
    "mana shield",
    "attribute shift",
}


def test_every_profiled_hero_gets_the_advisor_of_its_position_and_back():
    assert set(hero_aliases()) == set(SUPPORTED_HEROES)
    for hero, aliases in hero_aliases().items():
        expected = "support" if get_hero_position(hero) == "support" else "full"
        for name in (hero, *aliases):
            assert hero_coverage(name) == expected, name


def test_every_escape_or_defence_of_a_profile_can_be_named():
    from app.hero_profiles import load_hero_profile

    for hero in SUPPORTED_HEROES:
        profile = load_hero_profile(hero)
        for name in profile["key_escape_abilities"] + profile["key_defensive_abilities"]:
            assert name.lower() in USABLE_SAFETY | NOT_A_SAVE, (hero, name)


@pytest.mark.parametrize(
    ("npc", "hero", "position"),
    [
        ("npc_dota_hero_nevermore", "Shadow Fiend", "mid"),
        ("npc_dota_hero_queenofpain", "Queen of Pain", "mid"),
        ("npc_dota_hero_obsidian_destroyer", "Outworld Destroyer", "mid"),
        ("npc_dota_hero_shredder", "Timbersaw", "offlane"),
        ("npc_dota_hero_centaur", "Centaur Warrunner", "offlane"),
        ("npc_dota_hero_juggernaut", "Juggernaut", "carry"),
    ],
)
def test_live_names_and_positions(npc, hero, position):
    assert _normalize_hero_name(npc) == hero
    assert hero_coverage(hero) == "full"
    assert get_hero_position(hero) == position
    assert PLAYER_SERVICE.role_prior(hero) == {"role": position, "source": "hero"}


def test_a_hero_without_a_profile_keeps_its_name_and_the_safety_advice():
    assert _normalize_hero_name("npc_dota_hero_windrunner") == "Windranger"
    assert get_hero_position("Windranger") is None
    assert hero_coverage("Windranger") == "safety"


def test_offlane_lane_targets_are_lower():
    assert get_laning_thresholds("Axe", 10) == {
        "minute": 10,
        "expected_min": 25,
        "expected_max": 45,
    }
    assert get_laning_thresholds("Puck", 10)["expected_min"] == 45


def test_their_own_escapes_come_first_at_low_hp():
    qop = _extra(
        abilities={"ability0": _ability("queenofpain_blink")}, hero="npc_dota_hero_queenofpain"
    )
    assert low_hp_copy(qop, "Queen of Pain")[0] == "Use Blink now to get out, then reset HP."
    # Slardar's Guardian Sprint is "slardar_sprint" in GSI.
    slardar = _extra(
        abilities={"ability0": _ability("slardar_sprint")}, hero="npc_dota_hero_slardar"
    )
    assert (
        low_hp_copy(slardar, "Slardar")[0] == "Use Guardian Sprint now to get out, then reset HP."
    )
    ta = _extra(
        abilities={"ability0": _ability("templar_assassin_refraction")},
        hero="npc_dota_hero_templar_assassin",
    )
    assert low_hp_copy(ta, "Templar Assassin")[0] == "Use Refraction now and walk out of the fight."


def test_an_offlaner_is_held_to_an_offlaner_farm_pace():
    from app.advice_context import build_advice_context

    def quality(hero):
        return build_advice_context(
            {"hero": hero, "minute": 15, "extra_context": {"last_hits": 55}}
        )

    axe, jugg = quality("Axe"), quality("Juggernaut")
    assert axe["expected_lh_range"] == [52, 66] and axe["farm_quality"] == "okay"
    assert jugg["expected_lh_range"] == [75, 95] and jugg["farm_quality"] == "low"


def test_farm_pressure_uses_the_same_position_pace():
    from app.decision_points import _is_low_farm_rate

    def low(hero, minute, last_hits, gpm):
        return _is_low_farm_rate(
            {"hero": hero, "minute": minute, "extra_context": {"last_hits": last_hits, "gpm": gpm}}
        )

    # Axe on an offlaner's pace is not "behind"; the same numbers are for a carry.
    assert low("Axe", 10, 38, 380) is False
    assert low("Axe", 15, 60, 330) is False
    assert low("Juggernaut", 10, 38, 380) is True
    assert low("Juggernaut", 15, 60, 330) is True
    # Far behind even for an offlaner still counts.
    assert low("Axe", 15, 40, 250) is True


def test_the_site_heroes_page_lists_exactly_the_full_advisor(repo_root):
    """site/heroes.html: every supported hero once, in its position's group,
    with its portrait and the saves the coach can name (nothing more)."""
    import html
    import re

    from app.hero_profiles import load_hero_profile

    page = (repo_root / "site" / "heroes.html").read_text(encoding="utf-8")
    groups = dict(
        re.findall(
            r'<h3 class="heroes-group[^"]*" id="heroes-(\w+)">.*?</h3>\s*<ul[^>]*>(.*?)</ul>',
            page,
            re.S,
        )
    )
    assert set(groups) == {"carry", "mid", "offlane", "support"}
    listed = {}
    for position, block in groups.items():
        cards = re.findall(
            r'<a href="heroes/([a-z0-9-]+)\.html"><img src="assets/heroes/(\w+)\.webp"[^>]*/>'
            r"<span><b>([^<]+)</b>(?:<small>([^<]+)</small>)?",
            block,
        )
        heading = re.search(rf'id="heroes-{position}">.*?· (\d+)</h3>', page, re.S)
        assert heading and int(heading.group(1)) == len(cards), position
        for hero_page, key, name, saves in cards:
            name = html.unescape(name)
            assert (repo_root / "site" / "assets" / "heroes" / f"{key}.webp").is_file(), key
            # Every card opens the hero's own page, in both languages.
            assert (repo_root / "site" / "heroes" / f"{hero_page}.html").is_file(), hero_page
            assert (repo_root / "site" / "en" / "heroes" / f"{hero_page}.html").is_file(), hero_page
            assert get_hero_position(name) == position, name
            profile = load_hero_profile(name)
            expected = [
                a
                for a in profile["key_escape_abilities"] + profile["key_defensive_abilities"]
                if a.lower() in USABLE_SAFETY
            ]
            assert html.unescape(saves) == ", ".join(expected), name
            listed[name] = position
    assert sorted(listed) == sorted(SUPPORTED_HEROES)
    count = str(len(SUPPORTED_HEROES))
    assert f"для {count} героев" in page
    landing = (repo_root / "site" / "index.html").read_text(encoding="utf-8")
    assert f"для {count} героев" in landing and 'href="heroes.html"' in landing
