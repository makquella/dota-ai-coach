"""The safe-farm card says what this game looks like — a kill streak, the kill
score, the pace — instead of the same generic line every time."""

from __future__ import annotations

from app.advice_i18n import translate_ru
from app.post_laning_coach import build_post_laning_advice


def _advice(minute=20, **extra):
    state = {
        "hero": "Juggernaut",
        "minute": minute,
        "gold": 600,
        "hp_percent": 100,
        "extra_context": {"farm_quality": "good", **extra},
    }
    return build_post_laning_advice(state, "SAFE_FARMING")


def test_a_kill_streak_comes_first():
    advice = _advice(kill_streak=4, team_name="radiant", radiant_score=5, dire_score=20)
    assert advice.action == "Stay alive: you are on a 4-kill streak."
    assert translate_ru(advice.action) == "Берегите себя: у вас серия из 4 убийств подряд."
    assert translate_ru(advice.reason) != advice.reason


def test_the_kill_score_gap_changes_the_advice():
    behind = _advice(team_name="dire", radiant_score=21, dire_score=10)
    assert behind.action.startswith("Your team is 11 kills behind")
    assert translate_ru(behind.action).startswith("Команда отстаёт на 11 убийств")
    ahead = _advice(team_name="radiant", radiant_score=18, dire_score=9)
    assert ahead.action.startswith("Your team is 9 kills ahead")
    assert translate_ru(ahead.action).startswith("Команда впереди на 9 убийств")
    assert translate_ru(ahead.reason) != ahead.reason
    # A small gap, early in the game or without the team: not this line.
    assert "kills" not in _advice(team_name="radiant", radiant_score=12, dire_score=9).action
    assert (
        "kills"
        not in _advice(minute=10, team_name="radiant", radiant_score=1, dire_score=12).action
    )
    assert "kills" not in _advice(radiant_score=1, dire_score=12).action


def test_else_the_pace_in_numbers():
    advice = _advice(gpm=512, last_hits=140, minute=21)
    assert advice.reason == "Your pace: 512 gold per minute, 140 last hits at minute 21."
    assert (
        translate_ru(advice.reason)
        == "Ваш темп: 512 золота в минуту, добиваний к 21-й минуте: 140."
    )


def test_nothing_known_keeps_the_plain_line():
    assert _advice().action == "Keep farming the safest wave-and-camp route and reassess soon."
