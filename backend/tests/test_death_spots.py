"""Deaths that keep happening in one place: map spots and a route drill (map_analysis.py)."""

from __future__ import annotations

from app.advice_context import MAP_CENTER
from app.analysis_texts import render_analysis, render_finding
from app.map_analysis import analyze_map, death_spots

RIVER_MID = (MAP_CENTER, MAP_CENTER)
OWN_JUNGLE = (MAP_CENTER - 3000, MAP_CENTER - 1000)  # Radiant's half
ENEMY_JUNGLE = (MAP_CENTER + 3000, MAP_CENTER + 1000)


def _deaths(*places):
    return [{"t": 700 + 120 * i, "x": x + 10 * i, "y": y} for i, (x, y) in enumerate(places)]


def _facts(*places):
    return {"is_radiant": True, "deaths_log": _deaths(*places)}


def _finding(findings, finding_id):
    return next((f for f in findings if f["id"] == finding_id), None)


def test_spots_group_deaths_by_zone_and_half():
    _, _ = analyze_map(_facts(RIVER_MID))  # one death: no spot
    block, _ = analyze_map(_facts(RIVER_MID, OWN_JUNGLE, RIVER_MID, OWN_JUNGLE, RIVER_MID))
    assert [(s["zone"], s["side"], s["count"]) for s in block["spots"]] == [
        ("mid", "river", 3),
        ("jungle", "own", 2),
    ]
    assert block["spots"][0]["times"] == [700, 940, 1180]
    assert death_spots([]) == []


def test_three_deaths_by_the_river_get_a_route_drill():
    _, findings = analyze_map(_facts(RIVER_MID, RIVER_MID, OWN_JUNGLE, RIVER_MID))
    finding = _finding(findings, "deaths_same_place")
    assert finding["params"] == {
        "zone": "mid",
        "side": "river",
        "count": 3,
        "of": 4,
        "times": [700, 820, 1060],
    }
    ru = render_finding(finding, "ru")
    assert ru["title"] == "Смерти в одном месте: центральная линия у реки"
    assert ru["text"] == (
        "3 из 4 смертей — на центральной линии у реки (11:40, 13:40, 17:40). "
        "Здесь вас ловят раз за разом."
    )
    assert ru["drill"].startswith("Реку переходите, только когда на карте видно хотя бы троих")
    en = render_finding(finding, "en")
    assert en["title"] == "Deaths in one place: mid lane by the river"
    assert en["drill"].startswith("Cross the river only when")


def test_own_half_spot_gets_the_ward_drill_and_two_deaths_are_not_a_finding():
    _, findings = analyze_map(_facts(OWN_JUNGLE, OWN_JUNGLE, OWN_JUNGLE))
    finding = _finding(findings, "deaths_same_place")
    assert render_finding(finding, "ru")["drill"].startswith("Это ваша половина")
    _, findings = analyze_map(_facts(OWN_JUNGLE, OWN_JUNGLE))
    assert _finding(findings, "deaths_same_place") is None


def test_the_enemy_half_finding_names_the_spot_instead():
    _, findings = analyze_map(_facts(ENEMY_JUNGLE, ENEMY_JUNGLE, ENEMY_JUNGLE))
    assert _finding(findings, "deaths_same_place") is None
    enemy = _finding(findings, "deaths_enemy_half")
    assert enemy["params"]["spot_zone"] == "jungle"
    assert render_finding(enemy, "ru")["text"].endswith("Чаще всего — в лесу.")
    assert render_finding(enemy, "en")["text"].endswith("Most often in the jungle.")
    # Scattered deaths: the old text, no suffix.
    _, findings = analyze_map(
        _facts(
            ENEMY_JUNGLE,
            (MAP_CENTER + 6000, MAP_CENTER + 200),
            (MAP_CENTER + 200, MAP_CENTER + 6000),
        )
    )
    scattered = _finding(findings, "deaths_enemy_half")
    assert render_finding(scattered, "en")["text"].endswith("where the enemies were.")


def test_the_rendered_map_names_its_spots():
    block, findings = analyze_map(_facts(RIVER_MID, RIVER_MID))
    rendered = render_analysis({"map": block, "improvements": findings, "strengths": []}, "ru")
    assert rendered["map"]["spots"][0]["label"] == "центральная линия у реки"
