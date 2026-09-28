"""Role play in reviews: runes for a mid, stacks and sentries for a support."""

from __future__ import annotations

from app.analysis_texts import render_finding
from app.role_analysis import analyze_role


def _facts(**overrides):
    facts = {"parsed": True, "duration": 40 * 60, "rune_pickups": 6}
    facts.update(overrides)
    return facts


def _lineup(my_runes: int, enemy_runes: int) -> dict:
    """A parsed match: lanes decide the roles (lane_role 2 = mid)."""
    players = []
    for radiant in (True, False):
        for lane, lh in ((1, 300), (2, 250), (3, 150), (1, 40), (3, 30)):
            players.append(
                {"isRadiant": radiant, "lane_role": lane, "last_hits": lh, "hero": "Hero"}
            )
    players[1].update(me=True, rune_pickups=my_runes)
    players[6].update(hero="Storm Spirit", rune_pickups=enemy_runes)
    return {"duration": 40 * 60, "players": players}


def test_mid_behind_on_runes_against_the_enemy_mid():
    block, findings = analyze_role(_facts(rune_pickups=6), _lineup(6, 14), "mid")
    assert block == {
        "runes": 6,
        "runes_per_10": 1.5,
        "enemy_mid": "Storm Spirit",
        "enemy_runes": 14,
    }
    assert [f["id"] for f in findings] == ["runes_behind"]
    text = render_finding(findings[0], "ru")["text"]
    assert text.startswith("6 рун у вас против 14 у Storm Spirit")


def test_mid_rune_control_and_few_runes_without_a_lineup():
    _, good = analyze_role(_facts(rune_pickups=16), _lineup(16, 9), "mid")
    assert [f["id"] for f in good] == ["runes_good"]
    _, low = analyze_role(_facts(rune_pickups=3), None, "mid")
    assert [f["id"] for f in low] == ["runes_low"]
    assert render_finding(low[0], "en")["text"] == (
        "3 runes in 40 minutes. A mid without runes loses tempo and bottle charges."
    )


def test_support_stacks_and_sentries():
    facts = _facts(camps_stacked=1, sen_placed=0)
    block, findings = analyze_role(facts, None, "support")
    assert block == {"camps_stacked": 1, "sen_placed": 0}
    assert {f["id"] for f in findings} == {"stacks_low", "sentries_none"}
    assert render_finding(findings[0], "ru")["title"] == "Почти нет стаков"
    _, fine = analyze_role(_facts(camps_stacked=6, sen_placed=4), None, "support")
    assert fine == []


def test_only_parsed_long_enough_games_and_these_roles():
    assert analyze_role(_facts(parsed=False), None, "mid") == (None, [])
    assert analyze_role(_facts(duration=15 * 60), None, "mid") == (None, [])
    assert analyze_role(_facts(), None, "carry") == (None, [])
    assert analyze_role(_facts(rune_pickups=None), None, "mid") == (None, [])


def _offlane_lineup(my_stuns: float, enemy_stuns: float) -> dict:
    players = []
    for radiant in (True, False):
        for lane, lh in ((1, 300), (2, 250), (3, 150), (1, 40), (3, 30)):
            players.append(
                {"isRadiant": radiant, "lane_role": lane, "last_hits": lh, "hero": "Hero"}
            )
    players[2].update(me=True, stuns=my_stuns)
    players[7].update(hero="Mars", stuns=enemy_stuns)
    return {"duration": 40 * 60, "players": players}


def test_offlane_stuns_against_the_enemy_offlaner():
    block, findings = analyze_role(_facts(stuns=12.4), _offlane_lineup(12.4, 48.0), "offlane")
    assert block == {"stuns": 12, "enemy_offlane": "Mars", "enemy_stuns": 48}
    assert [f["id"] for f in findings] == ["stuns_behind"]
    assert render_finding(findings[0], "ru")["text"].startswith(
        "12 с оглушений у вас против 48 с у Mars"
    )
    _, good = analyze_role(_facts(stuns=60), _offlane_lineup(60, 20), "offlane")
    assert [f["id"] for f in good] == ["stuns_good"]
    # Close numbers or no lineup: nothing said.
    assert analyze_role(_facts(stuns=30), _offlane_lineup(30, 40), "offlane")[1] == []
    assert analyze_role(_facts(stuns=30), None, "offlane") == ({"stuns": 30}, [])


def test_offlane_building_damage_against_the_enemy_offlaner():
    lineup = _offlane_lineup(30, 30)
    lineup["players"][2]["tower_damage"] = 800
    lineup["players"][7]["tower_damage"] = 5200
    block, findings = analyze_role(_facts(stuns=30, tower_damage=800), lineup, "offlane")
    assert block["tower_damage"] == 800 and block["enemy_tower_damage"] == 5200
    assert [f["id"] for f in findings] == ["towers_behind"]
    assert render_finding(findings[0], "ru")["text"].startswith(
        "800 урона по строениям у вас против 5200 у Mars"
    )
    lineup["players"][7]["tower_damage"] = 2400  # 2× but a small gap: nothing
    assert analyze_role(_facts(stuns=30, tower_damage=800), lineup, "offlane")[1] == []


def test_a_dual_offlane_compares_with_the_core_not_the_support():
    lineup = _offlane_lineup(30, 90.0)
    # Their support also on the offlane, farming 2+ LH/min: both count as offlane.
    support = lineup["players"][9]
    support.update(lane_role=3, last_hits=90, hero="Crystal Maiden", stuns=5, obs_placed=2)
    lineup["players"].insert(7, lineup["players"].pop(9))  # listed before the core
    block, _ = analyze_role(_facts(stuns=30), lineup, "offlane")
    assert block["enemy_offlane"] == "Mars" and block["enemy_stuns"] == 90
