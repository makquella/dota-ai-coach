"""While dead with gold to spare, the death review says to buy first."""

from __future__ import annotations

from app.advice_i18n import translate_text
from app.post_laning_coach import build_post_laning_advice


def _dead(minute, gold, *, buyback_cost=None, alive=False, respawn=25):
    extra = {"alive": alive, "respawn_seconds": respawn, "available_gold": gold}
    if buyback_cost is not None:
        extra["buyback_cost"] = buyback_cost
    return {"minute": minute, "hp_percent": 0, "gold": gold, "extra_context": extra}


def test_spare_gold_while_dead_turns_into_a_purchase():
    advice = build_post_laning_advice(_dead(18, 2350), "DEATH_REVIEW")
    assert advice.category == "post_laning_death_route_reset"
    assert advice.action == (
        "Buy parts of your next item now with your 2350 gold: they wait for you at the fountain."
    )
    assert "safer route" in advice.reason
    assert translate_text(advice.action, "ru") == (
        "Купите части следующего предмета на 2350 золота сейчас — заберёте их у фонтана."
    )
    assert translate_text(advice.reason, "ru").startswith("Непотраченное золото")


def test_late_game_keeps_the_buyback_gold():
    advice = build_post_laning_advice(_dead(34, 4200, buyback_cost=2600), "DEATH_REVIEW")
    assert advice.action == "Buy parts of your next item with 1600 gold and keep 2600 for buyback."
    assert translate_text(advice.action, "ru") == (
        "Купите части следующего предмета на 1600 золота, а 2600 оставьте на байбэк."
    )
    # Not enough left after the buyback reserve, or the reserve is unknown: the
    # usual death review.
    usual = "Use the respawn time to choose a safer farming route."
    assert (
        build_post_laning_advice(_dead(34, 3000, buyback_cost=2600), "DEATH_REVIEW").action == usual
    )
    assert build_post_laning_advice(_dead(34, 9000), "DEATH_REVIEW").action == usual


def test_little_gold_or_alive_keeps_the_usual_texts():
    usual = "Use the respawn time to choose a safer farming route."
    assert build_post_laning_advice(_dead(18, 600), "DEATH_REVIEW").action == usual
    alive = build_post_laning_advice(_dead(18, 3000, alive=True, respawn=0), "SAFE_FARMING")
    assert alive is None or "Buy parts" not in alive.action


def test_other_death_reviews_carry_it_as_their_reason(client):
    from match_fixtures import gsi_match_stream

    seen = {}
    for payload in gsi_match_stream(minutes=8, death_minutes=(7,), step_seconds=5):
        client.post("/gsi", json=payload)
        response = client.get("/overlay/recommendation?lang=ru").json()
        if (
            response.get("status") == "active_advice"
            and response["decision_point"] == "DEATH_REVIEW"
        ):
            seen = response["recommendation"]
            break
    # Before minute 10 the death review keeps its own action; the reason is the purchase.
    assert seen["action"] == "Пока ждёте возрождения, продумайте более безопасный маршрут."
    assert seen["reason"] == (
        "Купите части следующего предмета на 1800 золота сейчас — заберёте их у фонтана."
    )
