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
    assert advice.action == "Keep farming: 512 gold per minute, 140 last hits at minute 21."
    assert (
        translate_ru(advice.action)
        == "Фармите дальше: 512 золота в минуту, добиваний к 21-й минуте: 140."
    )
    assert translate_ru(advice.reason) == (
        "Берите самые безопасные волны и лагеря: темп растёт и без рискованных драк."
    )


def test_nothing_known_keeps_the_plain_line():
    assert _advice().action == "Keep farming the safest wave-and-camp route and reassess soon."


def test_a_support_heartbeat_gets_no_farm_pace():
    from app.scheduler.heartbeat import _heartbeat_copy

    state = {
        "hero": "Crystal Maiden",
        "minute": 20,
        "hp_percent": 100,
        "extra_context": {"gpm": 300, "last_hits": 30, "advisor_coverage": "support"},
    }
    action, reason, _ = _heartbeat_copy(state)
    assert "pace" not in action + reason
    core = {**state, "extra_context": {**state["extra_context"], "advisor_coverage": "full"}}
    assert _heartbeat_copy(core)[0].startswith("Keep farming:")


def test_the_overlay_tells_the_scheduler_the_coverage(client, monkeypatch):
    from app.main import ADVICE_SCHEDULER

    seen = []
    original = ADVICE_SCHEDULER.evaluate

    def spy(request, *args, **kwargs):
        seen.append(request.extra_context.get("advisor_coverage"))
        return original(request, *args, **kwargs)

    monkeypatch.setattr(ADVICE_SCHEDULER, "evaluate", spy)
    client.post(
        "/gsi",
        json={
            "provider": {"name": "Dota 2"},
            "map": {"clock_time": 1200, "game_state": "DOTA_GAMERULES_STATE_GAME_IN_PROGRESS"},
            "player": {"gold": 900, "last_hits": 20, "deaths": 0, "gpm": 250},
            "hero": {
                "name": "npc_dota_hero_crystal_maiden",
                "level": 12,
                "health_percent": 20,
                "mana_percent": 100,
                "alive": True,
            },
        },
    )
    client.get("/overlay/recommendation")
    assert seen and seen[-1] == "support"


def test_a_pace_card_with_new_numbers_waits_four_minutes():
    from app.advice_scheduler import ADVICE_SCHEDULER
    from app.scheduler.hashing import _action_hash
    from app.schemas import RecommendationResponse

    def remaining(previous, action, at, *, pace_at=None, category="post_laning_safe_farm_route"):
        scheduler = ADVICE_SCHEDULER
        scheduler.state._last_shown_game_time_seconds = 720.0
        scheduler.state._last_shown_category = category
        scheduler.state._last_shown_action_hash = _action_hash(previous)
        scheduler.state._last_shown_decision_point = "SAFE_FARMING"
        scheduler.state._farm_pace_shown_game_time = pace_at
        recommendation = RecommendationResponse(
            action=action, reason="r", risk="r", priority="low", time_window="w", source="fallback"
        )
        left, _gap = scheduler._game_time_spacing_remaining_locked(
            decision_point="SAFE_FARMING",
            state={"minute": at // 60},
            recommendation=recommendation,
            advice_mode="coaching",
            category="post_laning_safe_farm_route",
            game_time_seconds=float(at),
        )
        return left

    pace = "Keep farming: {} gold per minute, {} last hits at minute {}."
    first = pace.format(444, 72, 12)
    # Only the numbers changed: the same advice, four minutes apart.
    assert remaining(first, pace.format(468, 84, 14), 840, pace_at=720.0) == 120
    assert remaining(first, pace.format(492, 96, 16), 960, pace_at=720.0) == 0
    recover = "Recover farm: {} last hits at minute {}, a good pace is {}+."
    assert (
        remaining(recover.format(138, 23, 150), recover.format(150, 25, 170), 840, pace_at=720.0)
        == 120
    )
    # Another card came in between (last shown at 12:00): the pace card shown
    # at 11:00 still waits until 15:00.
    item = "Use your gold: Black King Bar can be bought now."
    assert remaining(item, pace.format(468, 84, 14), 840, pace_at=660.0, category="x") == 60
    # Any other advice keeps the two minutes.
    other = "Keep farming toward Black King Bar on the safest waves and camps."
    assert remaining(other, other, 840) == 0
