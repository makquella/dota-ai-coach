"""Прокачка: an unspent skill point, the ultimate at 6/12/18 and a talent at
10/15/20/25, counted on changes so innates and missing fields stay quiet."""

from __future__ import annotations

from app.skill_tips import UNSPENT_STALE, UNSPENT_WAIT, SkillTips, read_skills


def _payload(level, levels, *, ult=0, talents=None, innate=None, attributes=None):
    abilities = {
        f"ability{i}": {"name": f"juggernaut_spell_{i}", "level": lvl, "ultimate": False}
        for i, lvl in enumerate(levels)
    }
    abilities[f"ability{len(levels)}"] = {
        "name": "juggernaut_omni_slash",
        "level": ult,
        "ultimate": True,
    }
    if innate is not None:
        abilities["ability9"] = {"name": "juggernaut_innate", "level": innate, "ultimate": False}
    hero = {"level": level}
    if talents is not None:
        hero.update({f"talent_{i + 1}": taken for i, taken in enumerate(talents)})
    if attributes is not None:
        hero["attributes_level"] = attributes
    return {"hero": hero, "abilities": abilities}


def _feed(tips, clock, payload):
    tips.observe(clock, read_skills(payload))


def test_no_blocks_no_skills():
    assert read_skills({"hero": {"level": 5}}) is None
    assert read_skills({"abilities": {"a": {"level": 1}}}) is None
    assert read_skills(None) is None


def test_a_point_left_unspent_is_named_after_a_short_wait():
    tips = SkillTips()
    _feed(tips, 100, _payload(3, [1, 1, 1]))
    _feed(tips, 110, _payload(4, [1, 1, 1]))  # levelled up, nothing spent
    assert tips.tip(110 + UNSPENT_WAIT - 1, "en", alive=True) is None
    hint = tips.tip(110 + UNSPENT_WAIT, "ru", alive=True)
    assert hint["title"] == "Не вложено очко навыков"
    assert hint["id"] == "skill-point@4"
    assert tips.tip(110 + UNSPENT_WAIT, "en", alive=False) is None
    # Spent → quiet.
    _feed(tips, 140, _payload(4, [2, 1, 1]))
    assert tips.tip(141, "en", alive=True) is None


def test_the_ultimate_is_named_at_six():
    tips = SkillTips()
    _feed(tips, 300, _payload(5, [2, 2, 1]))
    _feed(tips, 320, _payload(6, [2, 2, 1]))
    hint = tips.tip(320 + UNSPENT_WAIT, "en", alive=True)
    assert hint["title"] == "Learn your ultimate"
    assert "Omni Slash" in hint["hint"] and "level 6" in hint["hint"]
    _feed(tips, 340, _payload(6, [2, 2, 1], ult=1))
    assert tips.tip(341, "en", alive=True) is None


def test_the_talent_is_named_when_both_of_its_pair_are_open():
    tips = SkillTips()
    talents = [False] * 8
    _feed(tips, 900, _payload(9, [4, 3, 1], ult=1, talents=talents))
    _feed(tips, 910, _payload(10, [4, 3, 1], ult=1, talents=talents))
    hint = tips.tip(910 + UNSPENT_WAIT, "ru", alive=True)
    assert hint["title"] == "Выберите талант" and "10-го" in hint["hint"]
    talents[1] = True  # the right-hand level-10 talent
    _feed(tips, 930, _payload(10, [4, 3, 1], ult=1, talents=talents))
    assert tips.tip(931, "ru", alive=True) is None


def test_invoke_is_never_named_as_an_ultimate_to_learn():
    def payload(level, spent):
        abilities = {
            "ability0": {"name": "invoker_quas", "level": spent, "ultimate": False},
            "ability1": {"name": "invoker_invoke", "level": 1, "ultimate": True},
        }
        return {"hero": {"level": level}, "abilities": abilities}

    tips = SkillTips()
    _feed(tips, 900, payload(11, 7))
    _feed(tips, 910, payload(12, 7))  # a point owed, Invoke stays at 1
    hint = tips.tip(910 + UNSPENT_WAIT, "en", alive=True)
    assert hint is None or hint["title"] != "Learn your ultimate"


def test_an_innate_levelling_by_itself_never_reads_as_a_point_owed():
    tips = SkillTips()
    _feed(tips, 300, _payload(5, [2, 2, 1], innate=1))
    # Level 6: the ultimate and the innate both go up for one point.
    _feed(tips, 320, _payload(6, [2, 2, 1], ult=1, innate=2))
    assert tips.tip(400, "en", alive=True) is None
    # The next level is still counted from there.
    _feed(tips, 420, _payload(7, [2, 2, 1], ult=1, innate=2))
    assert tips.tip(420 + UNSPENT_WAIT, "en", alive=True)["id"] == "skill-point@7"


def test_without_talent_fields_only_the_ultimate_is_named_after_ten():
    tips = SkillTips()
    _feed(tips, 900, _payload(9, [4, 3, 1], ult=1))
    _feed(tips, 910, _payload(10, [4, 3, 1], ult=1))  # a talent taken, not visible
    assert tips.tip(910 + UNSPENT_WAIT, "en", alive=True) is None


def test_a_miscount_that_never_clears_stops_after_a_while():
    tips = SkillTips()
    talents = [False] * 8
    _feed(tips, 100, _payload(3, [1, 1, 1], talents=talents))
    # Attribute bonus taken, but no attributes_level field: looks owed.
    _feed(tips, 110, _payload(4, [1, 1, 1], talents=talents))
    _feed(tips, 110 + UNSPENT_STALE + 1, _payload(4, [1, 1, 1], talents=talents))
    assert tips.tip(110 + UNSPENT_STALE + 1, "en", alive=True) is None


def test_the_tip_shows_once_per_level():
    tips = SkillTips()
    _feed(tips, 100, _payload(3, [1, 1, 1]))
    _feed(tips, 110, _payload(4, [1, 1, 1]))
    start = 110 + UNSPENT_WAIT
    assert tips.tip(start, "en", alive=True) is not None
    assert tips.tip(start + 21, "en", alive=True) is None


def test_the_live_overlay_names_the_ultimate(client):
    def payload(clock, level, ult):
        return {
            "provider": {"name": "Dota 2"},
            "map": {"clock_time": clock, "game_state": "DOTA_GAMERULES_STATE_GAME_IN_PROGRESS"},
            "player": {"gold": 900, "last_hits": 40, "deaths": 0, "steamid": "76500000000000001"},
            "hero": {
                "name": "npc_dota_hero_juggernaut",
                "level": level,
                "health_percent": 100,
                "mana_percent": 100,
                "alive": True,
                "xpos": -6000,
                "ypos": -6600,
            },
            "abilities": {
                "ability0": {"name": "juggernaut_blade_fury", "level": 2, "ultimate": False},
                "ability1": {"name": "juggernaut_healing_ward", "level": 1, "ultimate": False},
                "ability2": {"name": "juggernaut_blade_dance", "level": 2, "ultimate": False},
                "ability3": {"name": "juggernaut_omni_slash", "level": ult, "ultimate": True},
            },
        }

    client.post("/gsi", json=payload(600, 5, 0))
    client.get("/overlay/recommendation")
    client.post("/gsi", json=payload(610, 6, 0))
    client.post("/gsi", json=payload(610 + UNSPENT_WAIT, 6, 0))
    hint = client.get("/overlay/recommendation?lang=ru").json().get("map_hint")
    assert hint and hint["title"] == "Изучите ультимейт"
    assert "Omnislash" in hint["hint"] or "Omni Slash" in hint["hint"]
