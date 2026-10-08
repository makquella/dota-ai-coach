"""GPM/XPM binding and policy upgrades through real HTTP/service/cache paths."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from match_fixtures import MATCH_ID, ME
from test_coach_ai import GOOD_MATCH_REVIEW, FakeLLM, _reviewed_match

from app.coach_review import COACH_VERSION, FactChecker, match_facts
from app.player_service import ASK_CACHE_KEY


@pytest.mark.parametrize(
    "text",
    [
        "You had 430 GPM.",
        "У вас 390 XPM.",
        "Gold per minute: 430.",
        "430 золота в минуту.",
        "GPM was 160.",
        "XPM: 2.",
        "You had -390 GPM.",
        "Anti-Mage had 390 GPM.",
        "Your team had 390 GPM.",
        "You had 390 GPM at 10:00.",
        "390 GPM in lane.",
        "У вас 390 GPM за первые 10 минут.",
    ],
)
def test_another_metric_or_subject_time_scope_never_licenses_a_match_rate(text: str) -> None:
    facts = {
        "hero": "Juggernaut",
        "match_rates": {"gpm": 390, "xpm": 430},
        "last_hits": 160,
        "at": "10:00",
        "other": {"gpm": 430, "xpm": 390},
        "enemy": "Anti-Mage",
    }
    assert FactChecker(json.dumps(facts), []).problems(text)


@pytest.mark.parametrize(
    "text",
    [
        "You had 390 GPM and 430 XPM.",
        "Ваш GPM: 390, XPM: 430.",
        "Gold per minute was 390.",
        "430 experience per minute.",
        "Золота в минуту: 390.",
        "430 опыта в минуту.",
    ],
)
def test_rates_match_their_own_fields_without_treating_the_unit_as_a_time_slice(text: str) -> None:
    facts = {"match_rates": {"gpm": 390, "xpm": 430}}
    assert FactChecker(json.dumps(facts), []).problems(text) == []


@pytest.mark.parametrize("value", [None, True, "390", -1, float("nan"), float("inf"), 2**53])
def test_invalid_rate_is_unknown_and_cannot_use_the_general_number_inventory(value: object) -> None:
    facts = match_facts({"analysis": {"headline": {"gpm": value, "last_hits": 390}}})
    assert facts is not None and facts["match_rates"] == facts["match_rates_evidence"] == {}
    assert "gpm" not in facts
    assert FactChecker(json.dumps(facts), []).problems("390 GPM.")


def test_zero_and_fractional_rates_remain_measured_values() -> None:
    facts = match_facts({"analysis": {"headline": {"gpm": 0, "xpm": 430.5}}})
    assert facts is not None and facts["match_rates"] == {"gpm": 0, "xpm": 430.5}
    assert facts["xpm"] == 430.5
    checker = FactChecker(json.dumps(facts), [])
    assert checker.problems("0 GPM, XPM: 430,5.") == []
    assert checker.problems("430 XPM.")
    assert facts["match_rates_evidence"]["gpm"]["observed_at"] is None


@pytest.mark.parametrize("language", ["ru", "en"])
def test_review_drops_swapped_rates_and_attaches_backend_evidence(
    client: TestClient, tmp_path: Path, language: str
) -> None:
    review = copy.deepcopy(GOOD_MATCH_REVIEW)
    review["summary"] += " You had 430 GPM. У вас 390 XPM."
    review["strengths"] = ["GPM: 390, XPM: 430."]
    review["next_game"] = ["Aim for 430 GPM."]
    provider = FakeLLM(review)
    service = _reviewed_match(client, tmp_path, provider)
    client.get(f"/player/matches/{MATCH_ID}?lang={language}")
    service.ai_jobs.run_pending(until=float("inf"))
    returned = client.get(f"/player/matches/{MATCH_ID}?lang={language}").json()["coach"]
    assert returned["state"] == "ready"
    assert returned["review"]["summary"] == GOOD_MATCH_REVIEW["summary"]
    assert returned["review"]["strengths"] == review["strengths"]
    assert returned["review"]["next_game"] == review["next_game"]
    expected = [
        {
            "source": "analysis.headline",
            "field": field,
            "observed_at": None,
            "precision": "reported_match_rate",
            "value": value,
        }
        for field, value in (("gpm", 390), ("xpm", 430))
    ]
    assert returned["review"]["rate_evidence"] == expected
    facts = json.loads(provider.calls[0][1]["content"])
    assert facts["match_rates_evidence"]["gpm"] == expected[0]
    assert "match_rates" in provider.calls[0][0]["content"]
    assert (
        service.store.cache_get(f"coach:match:{ME}:{MATCH_ID}:{language}")["verification_version"]
        == COACH_VERSION
    )


def test_question_retries_a_metric_swap_and_persists_verified_rates(
    client: TestClient, tmp_path: Path
) -> None:
    provider = FakeLLM({"answer": "You had 430 GPM."}, {"answer": "390 GPM and 430 XPM."})
    service = _reviewed_match(client, tmp_path, provider)
    result = client.post(
        f"/player/matches/{MATCH_ID}/ask?lang=en", json={"question": "What was my GPM?"}
    ).json()
    assert result["ok"] is True and result["answer"]["answer"] == "390 GPM and 430 XPM."
    assert len(provider.calls) == 2 and "gpm=430" in provider.calls[1][-1]["content"]
    history = service.store.cache_get(f"{ASK_CACHE_KEY}:{ME}:{MATCH_ID}")
    assert history[0]["rate_evidence"] == result["answer"]["rate_evidence"]
    assert history[0]["rate_evidence"][0]["field"] == "gpm"


def test_unverified_question_is_not_cached(client: TestClient, tmp_path: Path) -> None:
    provider = FakeLLM({"answer": "You had 430 GPM."})
    _reviewed_match(client, tmp_path, provider)
    result = client.post(
        f"/player/matches/{MATCH_ID}/ask?lang=en", json={"question": "What was my GPM?"}
    ).json()
    assert result == {"ok": False, "code": "unverified"} and len(provider.calls) == 2
    assert client.get(f"/player/matches/{MATCH_ID}?lang=en").json()["questions"] == []


def test_policy_upgrade_hides_v2_review_and_rechecks_saved_questions_offline(
    client: TestClient, tmp_path: Path
) -> None:
    service = _reviewed_match(client, tmp_path, None)
    coach_key = f"coach:match:{ME}:{MATCH_ID}:en"
    cached = {"hash": "old", "verification_version": 2, "review": {"summary": "430 GPM."}}
    service.store.cache_set(coach_key, cached)
    ask_key = f"{ASK_CACHE_KEY}:{ME}:{MATCH_ID}"
    history = [
        {"question": "GPM?", "answer": "430 GPM. Your GPM was 390.", "lang": "en"},
        {"question": "XPM?", "answer": "390 XPM.", "lang": "en"},
    ]
    service.store.cache_set(ask_key, history)
    body = client.get(f"/player/matches/{MATCH_ID}?lang=en").json()
    assert body["coach"] == {"state": "off"}
    assert len(body["questions"]) == 1 and body["questions"][0]["answer"] == "Your GPM was 390."
    assert body["questions"][0]["rate_evidence"][0]["value"] == 390
    assert (
        service.store.cache_get(coach_key) == cached and service.store.cache_get(ask_key) == history
    )
    service.llm = FakeLLM(GOOD_MATCH_REVIEW)
    assert client.get(f"/player/matches/{MATCH_ID}?lang=en").json()["coach"] == {"state": "pending"}
    service.ai_jobs.run_pending(until=float("inf"))
    ready = client.get(f"/player/matches/{MATCH_ID}?lang=en").json()["coach"]
    assert ready["state"] == "ready" and ready["review"]["rate_evidence"][0]["value"] == 390
