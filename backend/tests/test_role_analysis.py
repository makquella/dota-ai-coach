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
