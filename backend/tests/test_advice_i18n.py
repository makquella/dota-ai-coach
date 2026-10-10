"""Ukrainian advice text: translation rules and coverage of every visible text."""

from __future__ import annotations

import copy
import json
import random
import re

from app import gsi_state
from app.advice_i18n import (
    _RU_EXACT,
    localize_overlay_response,
    normalize_lang,
    translate_uk,
    translate_text,
)
from app.advice_scheduler import ADVICE_SCHEDULER
from app.coach_summary import COACH_SESSION_HISTORY
from app.main import _clear_demo_overlay_response
from app.match_memory import MATCH_MEMORY

LATIN_WORD = re.compile(r"[A-Za-z]{2,}")


def _reset_runtime() -> None:
    MATCH_MEMORY.reset()
    ADVICE_SCHEDULER.reset()
    COACH_SESSION_HISTORY.reset()
    _clear_demo_overlay_response()
    gsi_state.reset_latest_gsi()


def _visible_texts(response: dict) -> list[str]:
    texts = []
    for advice in (response.get("recommendation"), response.get("last_visible_advice")):
        if isinstance(advice, dict):
            texts += [advice.get("action"), advice.get("reason")]
    texts.append(response.get("message"))
    return [text for text in texts if isinstance(text, str) and text]


def test_normalize_lang():
    assert normalize_lang("uk") == "uk"
    assert normalize_lang("uk-UA") == "uk"
    assert normalize_lang("UK") == "uk"
    assert normalize_lang("en") == "en"
    assert normalize_lang("de") == "en"
    assert normalize_lang(None) == "en"


def test_translations_are_russian_apart_from_hp():
    for source, text in _RU_EXACT.items():
        leftovers = [word for word in LATIN_WORD.findall(text) if word != "HP"]
        assert not leftovers, (source, text)


def test_exact_and_patterned_texts():
    assert translate_uk("Leave the wave now and reset HP before rejoining.") == (
        "Ідіть із хвилі зараз і відновіть HP, перш ніж повернутися."
    )
    assert translate_uk("Avoid risky trades until Blade Fury is ready.") == (
        "Уникайте ризикованих розмінів, доки не готовий Blade Fury."
    )
    assert translate_uk("Without Blink, escaping a bad trade or fight is harder.") == (
        "Без Blink складніше вийти з невдалого розміну чи бійки."
    )
    assert translate_uk("Low mana reduces Medusa's effective survivability.") == (
        "У Medusa мало мани — виживаність помітно нижча."
    )


def test_consider_prefix_dash_and_whitespace_variants():
    assert translate_uk("Consider leave the wave now and reset HP before rejoining.") == (
        "Подумайте: ідіть із хвилі зараз і відновіть HP, перш ніж повернутися."
    )
    assert translate_uk("Monitoring lane - no urgent advice.") == (
        "Стежимо за лінією — термінових порад немає."
    )
    assert translate_uk("  Keep farming   safely. ") == "Продовжуйте спокійно фармити."


def test_truncated_text_uses_full_translation():
    source = (
        "Your farm pace is behind for this minute, but HP is stable, "
        "so the fastest recovery is clean last hitting."
    )
    truncated = source[:80].rstrip() + "..."
    assert translate_uk(truncated) == _RU_EXACT[source]


def test_unknown_text_stays_english():
    assert translate_uk("Something the table does not know.") is None
    assert translate_text("Something the table does not know.", "uk") == (
        "Something the table does not know."
    )
    # Never half-translated: one unknown sentence keeps the whole text English.
    mixed = "Keep farming safely. Something the table does not know."
    assert translate_text(mixed, "uk") == mixed


def test_english_is_unchanged():
    response = {"recommendation": {"action": "Keep farming safely."}, "message": "Monitoring..."}
    assert localize_overlay_response(response, "en") is response


def test_localize_overlay_response_translates_visible_fields_only():
    response = {
        "status": "active_advice",
        "recommendation": {
            "action": "Keep farming safely.",
            "reason": "HP is stable and no pressure signal is active.",
            "risk": "Low risk if you keep playing safely.",
            "priority": "low",
        },
        "last_visible_advice": {"action": "Focus on safe last hits."},
        "message": "Monitoring...",
    }
    localized = localize_overlay_response(response, "uk")
    assert localized["recommendation"]["action"] == "Продовжуйте спокійно фармити."
    assert localized["recommendation"]["reason"] == "HP у нормі, ознак тиску немає."
    assert localized["recommendation"]["risk"] == "Low risk if you keep playing safely."
    assert localized["recommendation"]["priority"] == "low"
    assert localized["last_visible_advice"]["action"] == "Зосередьтеся на безпечних добиваннях."
    assert localized["message"] == "Стежимо за грою…"
    # The original payload (also kept in history) is not modified.
    assert response["recommendation"]["action"] == "Keep farming safely."


def test_overlay_endpoint_lang_param(client, repo_root):
    sample = repo_root / "data" / "gsi_samples" / "low_hp_juggernaut.json"
    client.post("/gsi", json=json.loads(sample.read_text(encoding="utf-8")))
    ukrainian = client.get("/overlay/recommendation?lang=uk").json()
    english = client.get("/overlay/recommendation").json()

    assert ukrainian["lang"] == "uk"
    assert "lang" not in english
    # First call creates the advice ("advice"), the second shows it ("active_advice").
    assert ukrainian["recommendation"] and english["recommendation"]
    assert ukrainian["recommendation"]["action"] == translate_uk(
        english["recommendation"]["action"]
    )
    assert ukrainian["recommendation"]["reason"] == translate_uk(
        english["recommendation"]["reason"]
    )
    # History keeps the canonical English text.
    assert COACH_SESSION_HISTORY.records()[-1]["action"] == english["recommendation"]["action"]


def test_recent_advice_lang_param(client, repo_root):
    sample = repo_root / "data" / "gsi_samples" / "low_hp_juggernaut.json"
    client.post("/gsi", json=json.loads(sample.read_text(encoding="utf-8")))
    shown = client.get("/overlay/recommendation").json()["recommendation"]

    english = client.get("/advice/recent").json()["items"]
    ukrainian = client.get("/advice/recent?lang=uk").json()["items"]

    assert english[0]["action"] == shown["action"]
    assert ukrainian[0]["action"] == translate_uk(shown["action"])
    assert ukrainian[0]["reason"] == translate_uk(shown["reason"])
    assert ukrainian[0]["priority"] == english[0]["priority"]


def _mutate(payload: dict, clock: int, rng: random.Random) -> dict:
    payload = copy.deepcopy(payload)
    game_map = payload.setdefault("map", {})
    game_map["clock_time"] = clock
    game_map["game_time"] = clock
    game_map["game_state"] = "DOTA_GAMERULES_STATE_GAME_IN_PROGRESS"
    hero = payload.setdefault("hero", {})
    hero["health_percent"] = rng.choice([4, 9, 15, 22, 30, 38, 50, 70, 100])
    hero["mana_percent"] = rng.choice([3, 10, 20, 40, 90])
    dead = rng.random() < 0.1
    hero["alive"] = not dead
    hero["respawn_seconds"] = rng.choice([5, 20, 45]) if dead else 0
    for key in ("stunned", "silenced", "hexed", "smoked"):
        hero[key] = rng.random() < 0.08
    for ability in (payload.get("abilities") or {}).values():
        if isinstance(ability, dict) and rng.random() < 0.4:
            ability["cooldown"] = rng.choice([0, 0, 8, 20])
            ability["can_cast"] = ability["cooldown"] == 0
    player = payload.setdefault("player", {})
    if rng.random() < 0.3:
        player["deaths"] = int(player.get("deaths", 0)) + rng.choice([0, 1, 2])
    if rng.random() < 0.5:
        player["last_hits"] = max(0, int(player.get("last_hits", 0)) + rng.choice([-30, 0, 20]))
    return payload


def test_every_visible_text_from_fixtures_has_ukrainian(client, repo_root):
    """Replays and live GSI samples (plus mutations) must never show English in uk."""
    untranslated: set[str] = set()

    def check(response: dict) -> None:
        for text in _visible_texts(response):
            if translate_uk(text) is None:
                untranslated.add(text)

    for path in sorted((repo_root / "data/match_simulations").glob("*.jsonl")):
        _reset_runtime()
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                check(client.post("/demo/replay-state", json=json.loads(line)).json()["overlay"])

    samples = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted((repo_root / "data/gsi_samples").glob("*.json"))
    ]
    assert samples
    rng = random.Random(7)
    for index in range(len(samples) + 120):
        _reset_runtime()
        base = samples[index % len(samples)]
        clock = rng.choice([60, 200, 400, 550, 700, 900, 1300, 2000, 2800])
        steps = 1 if index < len(samples) else rng.choice([3, 8, 20])
        for _ in range(steps):
            if index >= len(samples):
                if rng.random() < 0.3:
                    base = rng.choice(samples)
                clock += rng.choice([2, 5, 15, 40, 90])
                payload = _mutate(base, clock, rng)
            else:
                payload = base
            client.post("/gsi", json=payload)
            check(client.get("/overlay/recommendation").json())

    assert not untranslated, sorted(untranslated)


def test_coaching_rewording_keeps_english_grammatical():
    from app.advice_ux_policy import _coaching_action

    assert _coaching_action("Farm back your buyback gold before the next purchase.") == (
        "Consider: farm back your buyback gold before the next purchase."
    )
    # Both spellings translate (history written before the colon keeps working).
    for text in (
        "Consider: farm back your buyback gold before the next purchase.",
        "Consider farm back your buyback gold before the next purchase.",
    ):
        assert translate_uk(text).startswith("Подумайте: нафарміть")
