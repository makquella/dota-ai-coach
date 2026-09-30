"""Which ability to level next, from how pro players level the hero
(app/skill_build.py): the maxing order of recent pro games, the live skill tip
and the game plan line."""

from __future__ import annotations

import copy
from typing import Any

from app.game_plan import build_game_plan
from app.opendota import OpenDotaClient
from app.player_api import PLAYER_SERVICE
from app.skill_build import next_skill, skill_order, upgrade_names
from app.skill_tips import UNSPENT_WAIT, SkillTips, read_skills

FURY, WARD, DANCE, OMNI = (
    "juggernaut_blade_fury",
    "juggernaut_healing_ward",
    "juggernaut_blade_dance",
    "juggernaut_omni_slash",
)
TALENT = "special_bonus_unique_juggernaut_3"
# Blade Fury maxed first, then Blade Dance, Healing Ward last; the ultimate and
# talents never reach a 4th level.
GAME = [
    FURY,
    DANCE,
    FURY,
    DANCE,
    FURY,
    OMNI,
    FURY,
    DANCE,
    DANCE,
    TALENT,
    WARD,
    OMNI,
    WARD,
    WARD,
    WARD,
]
NAMES = {FURY: "Blade Fury", DANCE: "Blade Dance", WARD: "Healing Ward", OMNI: "Omnislash"}
DATA = {"orders": [GAME, GAME, GAME[:9] + [WARD, WARD, WARD, WARD]], "names": NAMES}


def test_the_maxing_order_of_pro_games():
    build = skill_order(DATA)
    assert build["order"] == [FURY, DANCE, WARD]
    assert build["names"][FURY] == "Blade Fury"
    assert build["first_agree"] == 3 and build["games"] == 3
    assert skill_order({"orders": [GAME, GAME]}) is None  # two games are not a pattern
    assert skill_order(None) is None
    assert skill_order({"orders": [[TALENT], [TALENT], [TALENT]]}) is None


def test_shadowraze_is_one_skill_in_three_slots():
    raze = ["nevermore_shadowraze1", "nevermore_shadowraze2", "nevermore_shadowraze3"]
    ids = {"1": raze[0], "2": raze[1], "3": raze[2], "4": "nevermore_dark_lord"}
    game = upgrade_names([3, 4, 2, 4, 1, 4, 3, 4], ids)
    assert game.count("nevermore_shadowraze1") == 4
    build = skill_order({"orders": [game] * 3})
    assert build["order"] == ["nevermore_shadowraze1", "nevermore_dark_lord"]
    assert upgrade_names([9, "x"], ids) == [] and upgrade_names(None, ids) == []


def test_the_next_point_follows_the_order_within_the_level_caps():
    build = skill_order(DATA)
    # Level 3: Blade Fury 2 (the cap is 2) → the next in the order.
    assert next_skill(build, {FURY: 2, DANCE: 0, WARD: 0}, 3) == DANCE
    assert next_skill(build, {FURY: 1, DANCE: 1, WARD: 0}, 3) == FURY
    assert next_skill(build, {FURY: 4, DANCE: 4, WARD: 3}, 16) == WARD
    assert next_skill(build, {FURY: 4, DANCE: 4, WARD: 4}, 20) is None
    # Another hero's order (a random or a swap): nothing to say.
    assert next_skill(build, {"axe_berserkers_call": 1}, 3) is None
    assert next_skill(None, {FURY: 1}, 3) is None


def _payload(level, fury, dance, ward, ult=0):
    abilities = {
        "ability0": {"name": FURY, "level": fury, "ultimate": False},
        "ability1": {"name": WARD, "level": ward, "ultimate": False},
        "ability2": {"name": DANCE, "level": dance, "ultimate": False},
        "ability3": {"name": OMNI, "level": ult, "ultimate": True},
    }
    return {"hero": {"level": level}, "abilities": abilities}


def test_the_skill_tip_names_the_ability():
    build = skill_order(DATA)
    tips = SkillTips()
    tips.observe(100, read_skills(_payload(2, 1, 1, 0)))
    tips.observe(110, read_skills(_payload(3, 1, 1, 0)))
    hint = tips.tip(110 + UNSPENT_WAIT, "ru", alive=True, build=build)
    assert hint["title"] == "Вложите очко в Blade Fury"
    assert hint["hint"] == (
        "Порядок прокачки у про-игроков на этом герое: Blade Fury → Blade Dance → Healing Ward."
    )
    # Without the pro order: the plain line.
    assert tips.tip(110 + UNSPENT_WAIT, "en", alive=True)["title"] == "Unspent skill point"


def test_the_ultimate_takes_its_in_game_name_from_the_build():
    build = skill_order(DATA)
    tips = SkillTips()
    tips.observe(300, read_skills(_payload(5, 3, 1, 1)))
    tips.observe(320, read_skills(_payload(6, 3, 1, 1)))
    hint = tips.tip(320 + UNSPENT_WAIT, "en", alive=True, build=build)
    assert hint["title"] == "Learn your ultimate" and "Omnislash" in hint["hint"]


def test_the_game_plan_names_the_pro_order():
    plan = build_game_plan(
        hero="Juggernaut", history=[], all_recent=[], meta=None, lang="ru", skills=skill_order(DATA)
    )
    assert "Прокачка у про: сначала Blade Fury, потом Blade Dance" in plan["lines"]
    plan = build_game_plan(
        hero="Juggernaut", history=[], all_recent=[], meta=None, lang="en", skills=None
    )
    assert not any("Pros max" in line for line in (plan or {}).get("lines", []))


class _Session:
    """requests.Session stand-in answering by path."""

    def __init__(self, routes: dict[str, Any]):
        self.routes = routes
        self.paths: list[str] = []

    def request(self, method: str, url: str, **kwargs: Any) -> Any:
        path = "/" + url.split("/api/", 1)[1]
        self.paths.append(path)
        body = self.routes.get(path)

        class _Response:
            status_code = 200 if body is not None else 404

            def json(self) -> Any:
                return copy.deepcopy(body)

        return _Response()


def test_the_client_reads_recent_pro_games():
    ids = {"1": FURY, "2": DANCE, "3": WARD, "4": OMNI, "5": TALENT}
    upgrades = [1, 2, 1, 2, 1, 4, 1, 2, 2, 5, 3]
    player = {"hero_id": 8, "ability_upgrades_arr": upgrades}
    routes = {
        "/constants/ability_ids": ids,
        "/heroes/8/matches": [{"match_id": 10}, {"match_id": 11}, {"match_id": 12}],
        "/matches/10": {"players": [{"hero_id": 1}, player]},
        # 11: not on OpenDota → skipped
        "/matches/12": {"players": [{"hero_id": 8, "ability_upgrades_arr": None}]},
        "/constants/abilities": {
            FURY: {"dname": "Blade Fury"},
            TALENT: {"dname": "+20 Attack Speed"},
        },
    }
    session = _Session(routes)
    data = OpenDotaClient(session=session, min_interval=0).pro_skill_orders(8)
    assert data["orders"] == [
        [FURY, DANCE, FURY, DANCE, FURY, OMNI, FURY, DANCE, DANCE, TALENT, WARD]
    ]
    assert data["names"] == {FURY: "Blade Fury"}  # talents never named


def test_the_service_fetches_once_and_reads_the_cache(monkeypatch):
    service = PLAYER_SERVICE
    calls = []

    class _Client:
        def pro_skill_orders(self, hero_id):
            calls.append(hero_id)
            return DATA

    monkeypatch.setattr(service, "client", _Client())
    assert service.skill_build("Juggernaut") is None  # nothing cached yet: fetched
    service.jobs.run_pending(until=float("inf"))
    assert calls == [8]
    service._plans.clear()
    assert service.skill_build("Juggernaut")["order"] == [FURY, DANCE, WARD]
    service.jobs.run_pending(until=float("inf"))
    assert calls == [8]  # fresh: not fetched again
    assert service.skill_build("Not A Hero") is None
