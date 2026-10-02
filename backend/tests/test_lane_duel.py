"""The lane minute by minute against its enemy core (lane_duel.py)."""

from __future__ import annotations

from app.analysis_texts import render_finding
from app.focus_goal import match_result
from app.lane_duel import analyze_lane, lane_series
from app.opendota import trim_match


def _curve(per_minute: int, minutes: int = 12) -> list[int]:
    return [per_minute * m for m in range(minutes + 1)]


HERO_IDS = {
    "Juggernaut": 8,
    "Crystal Maiden": 5,
    "Axe": 2,
    "Rubick": 86,
    "Riki": 32,
    "Lina": 25,
}


def _player(hero, *, radiant, lane, lh, gold, roaming=False, account=None):
    return {
        "account_id": account,
        "hero_id": HERO_IDS[hero],
        "isRadiant": radiant,
        "lane": lane,
        "is_roaming": roaming,
        "lh_t": _curve(lh),
        "dn_t": _curve(1),
        "gold_t": _curve(gold),
        "xp_t": _curve(400),
    }


def _match(my_gold=300, enemy_gold=400):
    raw = {
        "match_id": 1,
        "version": 22,  # parsed
        "duration": 2400,
        "players": [
            _player("Juggernaut", radiant=True, lane=1, lh=5, gold=my_gold, account=11),
            _player("Crystal Maiden", radiant=True, lane=1, lh=1, gold=200, account=12),
            _player("Axe", radiant=False, lane=1, lh=3, gold=enemy_gold, account=13),
            _player("Rubick", radiant=False, lane=1, lh=0, gold=220, account=14),
            _player("Riki", radiant=False, lane=1, lh=4, gold=900, roaming=True, account=15),
            _player("Lina", radiant=False, lane=2, lh=6, gold=500, account=16),
        ],
    }
    return trim_match(raw, 11)


def test_trim_match_keeps_ten_minutes_of_everyone():
    trimmed = _match()
    axe = next(p for p in trimmed["players"] if p["hero"] == "Axe")
    assert len(axe["lane_t"]["gold"]) == 11 and "gold_t" not in axe
    assert lane_series(axe, "lh")[10] == 30
    me = next(p for p in trimmed["players"] if p.get("me"))
    assert lane_series(me, "gold")[10] == 3000


def test_a_lost_lane_names_the_enemy_core_and_when_it_turned():
    block, findings = analyze_lane(_match(), "carry")
    assert block["enemy"] == "Axe"  # the core of the lane, not the roaming Riki
    assert block["enemies"] == ["Axe", "Rubick"]
    assert block["gold_diff"] == -1000 and block["result"] == "lost"
    assert block["turn"] == 3  # 100 gold a minute: 300 behind from minute 3
    assert block["total_diff"] == (3000 + 2000) - (4000 + 2200)
    assert [p["minute"] for p in block["points"]] == [3, 5, 7, 10]
    assert block["points"][-1]["lh"] == 50 and block["points"][-1]["enemy_lh"] == 30
    (finding,) = findings
    assert finding["id"] == "lane_lost" and finding["params"]["gold"] == 1000
    ru = render_finding(finding, "ru")
    assert ru["title"] == "Линия против Axe проиграна"
    assert "50 добиваний у вас против 30 у Axe" in ru["text"]
    assert "разрыв появился с 3-й минуты" in ru["text"]
    en = render_finding(finding, "en")
    assert "1000 gold behind; the gap opened at minute 3" in en["text"]


def test_won_even_and_support_lanes():
    block, findings = analyze_lane(_match(my_gold=500), "offlane")
    assert block["result"] == "won" and findings[0]["id"] == "lane_won"
    assert findings[0]["kind"] == "strength"
    block, findings = analyze_lane(_match(my_gold=380), "carry")
    assert block["result"] == "even" and block["turn"] is None and findings == []
    # A support's lane is shown, never judged.
    block, findings = analyze_lane(_match(), "support")
    assert block["result"] == "lost" and not block["judged"] and findings == []


def test_no_lane_without_a_parsed_replay_or_a_lane():
    trimmed = _match()
    assert analyze_lane({**trimmed, "parsed": False}, "carry") == (None, [])
    me = next(p for p in trimmed["players"] if p.get("me"))
    me["is_roaming"] = True
    assert analyze_lane(trimmed, "carry") == (None, [])
    assert analyze_lane(None, "carry") == (None, [])


def test_the_focus_on_a_lost_lane_needs_a_lane():
    focus = {"id": "lane_lost", "family": "lane_lost", "section": "laning"}
    assert match_result({"problems": [], "sections": {"laning": {}}, "lane": None}, focus) is None
    assert match_result({"problems": [], "sections": {"laning": {}}, "lane": {"x": 1}}, focus)


def test_the_career_counts_the_judged_lanes():
    from app.lane_duel import career_lanes

    def match(mid, result, enemy, diff, judged=True):
        lane = {
            "judged": judged,
            "result": result,
            "enemy": enemy,
            "gold_diff": diff,
            "hero": "Juggernaut",
            "hero_id": 8,
        }
        return {"match_id": mid, "analysis": {"lane": lane}}

    newest_first = [
        match(5, "lost", "Axe", -1200),
        match(4, "won", "Mars", 900),
        match(3, "lost", "Axe", -900),
        match(2, "even", "Lina", 100, judged=False),  # a support's lane: not counted
        match(1, "even", "Lina", 0),
        {"match_id": 0, "analysis": {"lane": None}},
    ]
    lanes = career_lanes(newest_first)
    assert (lanes["games"], lanes["won"], lanes["even"], lanes["lost"]) == (4, 1, 1, 2)
    assert lanes["gold_diff"] == -300
    assert [g["match_id"] for g in lanes["games_list"]] == [1, 3, 4, 5]  # oldest first
    assert lanes["hard"] == [{"hero": "Axe", "lost": 2}]
    assert career_lanes(newest_first[:2]) is None
