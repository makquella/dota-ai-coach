"""Live "no farm lately" signal and farm-pace numbers in post-laning advice."""

from __future__ import annotations

from typing import Any

from match_fixtures import gsi_match_stream

from app.advice_i18n import translate_ru
from app.farm_tracker import FarmTracker
from app.match_memory import MATCH_MEMORY
from app.post_laning_coach import build_post_laning_advice


def _feed(tracker: FarmTracker, plan: list[tuple[int, int, float, bool]]) -> None:
    """plan: (from_clock, to_clock, last hits per minute, alive)."""
    last_hits = 0.0
    for start, end, rate, alive in plan:
        for clock in range(start, end, 5):
            last_hits += rate * 5 / 60
            tracker.observe(clock, int(last_hits), alive)


def test_stall_after_minutes_without_last_hits():
    tracker = FarmTracker()
    _feed(tracker, [(0, 14 * 60, 6.0, True), (14 * 60, 18 * 60 + 5, 0.5, True)])
    stall = tracker.stall()
    assert stall is not None
    assert stall["minutes"] == 4 and stall["last_hits"] <= 3 and stall["since_clock"] == 840


def test_no_stall_while_farming_dead_as_support_or_early():
    farming = FarmTracker()
    _feed(farming, [(0, 18 * 60, 6.0, True)])
    assert farming.stall() is None

    dead = FarmTracker()  # dead most of the window: not a farm stall
    _feed(dead, [(0, 14 * 60, 6.0, True), (14 * 60, 18 * 60, 0.0, False)])
    assert dead.stall() is None

    support = FarmTracker()  # never farmed much: supports get no stall advice
    _feed(support, [(0, 14 * 60, 1.5, True), (14 * 60, 18 * 60, 0.0, True)])
    assert support.stall() is None

    early = FarmTracker()
    _feed(early, [(0, 6 * 60, 6.0, True), (6 * 60, 11 * 60, 0.0, True)])
    assert early.stall() is None


def test_rewind_or_gap_breaks_the_window():
    tracker = FarmTracker()
    _feed(tracker, [(0, 14 * 60, 6.0, True)])
    tracker.observe(16 * 60, tracker.samples[-1][1], True)  # 2 minutes missing
    tracker.observe(18 * 60 + 5, tracker.samples[-1][1], True)
    assert tracker.stall() is None
    tracker.observe(60, 2, True)  # replay seek back: history starts over
    assert len(tracker.samples) == 1


def _post_state(**extra: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "farm_quality": "good",
        "last_hits": 100,
        "hp_pressure_state": "healthy",
        "position_zone": "lane_area",
        "position_risk": "low",
        "missing_signals": [],
    }
    base.update(extra)
    return {
        "hero": "Juggernaut",
        "minute": 18,
        "hp_percent": 80,
        "game_state": "calm farming",
        "team_status": "unknown",
        "extra_context": base,
    }


def test_post_laning_farm_stall_advice_with_numbers():
    stall = {"minutes": 4, "last_hits": 2, "since_clock": 840}
    advice = build_post_laning_advice(_post_state(farm_stall=stall), "SAFE_FARMING")
    assert advice is not None and advice.category == "post_laning_farm_stall"
    assert advice.reason == (
        "Only 2 last hits in the last 4 minutes; every minute without farm delays your next item."
    )
    assert translate_ru(advice.reason) == (
        "Добиваний за последние 4 мин: 2. Каждая минута без фарма отодвигает следующий предмет."
    )
    assert translate_ru(advice.action) == (
        "Вернитесь к фарму: заберите ближайшую безопасную волну или лагерь."
    )
    # Under pressure, safety first.
    pressured = build_post_laning_advice(
        _post_state(farm_stall=stall, hp_pressure_state="risky"), "SAFE_FARMING"
    )
    assert pressured is not None and pressured.category == "post_laning_pressure_avoidance"


def test_farm_recovery_names_the_pace():
    state = _post_state(farm_quality="low", last_hits=38, expected_lh_range=[98, 126])
    advice = build_post_laning_advice(state, "SAFE_FARMING")
    assert advice is not None and advice.category == "post_laning_farm_recovery"
    assert advice.reason == (
        "You have 38 last hits at minute 18; a good pace is 98+, so rebuild farm before forcing fights."
    )
    assert translate_ru(advice.reason) == (
        "Добиваний к 18-й минуте: 38, хороший темп — 98+. "
        "Сначала восстановите фарм, потом ищите драки."
    )


def test_live_gsi_stall_reaches_the_overlay(client):
    shown: list[str] = []
    for payload in gsi_match_stream(minutes=22, death_minutes=(), step_seconds=5):
        clock = payload["map"]["clock_time"]
        if clock >= 14 * 60:
            payload["player"]["last_hits"] = 84  # farm stops at 14:00
        client.post("/gsi", json=payload)
        if clock >= 18 * 60 and clock % 15 == 0:
            response = client.get("/overlay/recommendation?lang=ru").json()
            reason = (response.get("recommendation") or {}).get("reason") or ""
            shown.append(reason)
    assert MATCH_MEMORY.farm.stall() is not None
    assert any(text.startswith("Добиваний за последние") for text in shown), shown[-5:]
