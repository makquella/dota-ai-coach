"""Metric binding is deterministic; provider scripts exercise real HTTP/cache paths."""

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
        "You had 200 kills.",
        "У вас 200 убийств.",
        "Kills: 200, deaths: 5.",
        "Убийств было 200.",
        "Смерти: их было 2.",
        "You had 8 deaths.",
        "5 assists, 2 kills.",
        "KDA 2/4/5.",
        "2 kills on lane.",
        "2 убийства к 10:00.",
        "Anti-Mage had 2 kills.",
        "You had 0.2k kills.",
        "2.4 kills.",
        "-2 kills.",
        "Kills: -2.",
        "У вас −2 убийства.",
        "The enemy had 2 kills.",
        "KDA -2/5/4.",
    ],
)
def test_unrelated_or_small_numbers_never_license_a_combat_counter(text: str) -> None:
    facts = {
        "hero": "Juggernaut",
        "match_totals": {"kills": 2, "deaths": 5, "assists": 4},
        "last_hits": 200,
        "time": "10:00",
        "other": {"kills": 200, "deaths": 8},
        "enemy": "Anti-Mage",
    }
    assert FactChecker(json.dumps(facts), []).problems(text)


@pytest.mark.parametrize(
    "text", ["2 kills, 5 deaths, 4 assists.", "Смертей: 5, убийств: 2, ассистов: 4.", "KDA 2/5/4."]
)
def test_correct_field_bound_totals_are_kept(text: str) -> None:
    facts = {"kills": 2, "deaths": 5, "assists": 4}
    assert FactChecker(json.dumps(facts), []).problems(text) == []


def test_missing_and_zero_totals_are_distinct() -> None:
    facts = match_facts({"analysis": {"headline": {"kills": 0}}})
    assert facts is not None and facts["match_totals"] == {"kills": 0}
    checker = FactChecker(json.dumps(facts), [])
    assert checker.problems("0 kills.") == []
    assert checker.problems("0 deaths.")
    unknown = match_facts({"analysis": {"headline": {"kills": True, "deaths": -1}}})
    assert unknown is not None and unknown["match_totals"] == {}
    assert FactChecker(json.dumps(unknown), []).problems("2 kills.")


def test_review_scrubs_metric_swaps_without_removing_future_goals(
    client: TestClient, tmp_path: Path
) -> None:
    answer = copy.deepcopy(GOOD_MATCH_REVIEW)
    answer["summary"] += " У вас 160 убийств. У вас 2 смерти. KDA 9/3/6."
    answer["strengths"] = ["У вас 3 убийства и 6 ассистов."]
    provider = FakeLLM(answer)
    service = _reviewed_match(client, tmp_path, provider)
    client.get(f"/player/matches/{MATCH_ID}?lang=ru")
    service.ai_jobs.run_pending(until=float("inf"))
    coach = client.get(f"/player/matches/{MATCH_ID}?lang=ru").json()["coach"]
    assert coach["state"] == "ready"
    review = coach["review"]
    assert review["summary"] == GOOD_MATCH_REVIEW["summary"]
    assert review["strengths"] == answer["strengths"]
    assert review["next_game"] == GOOD_MATCH_REVIEW["next_game"]
    assert review["counter_evidence"] == [
        {
            "source": "analysis.headline",
            "field": field,
            "observed_at": None,
            "precision": "reported_total",
            "value": value,
        }
        for field, value in (("kills", 3), ("deaths", 9), ("assists", 6))
    ]
    facts = json.loads(provider.calls[0][1]["content"])
    assert facts["match_totals_evidence"]["kills"] == review["counter_evidence"][0]
    assert "match_totals" in provider.calls[0][0]["content"]
    assert COACH_VERSION == 3


def test_question_swapped_metrics_retry_and_cache_only_verified_answer(
    client: TestClient, tmp_path: Path
) -> None:
    provider = FakeLLM(
        {"answer": "You had 160 kills."}, {"answer": "You had 3 kills and 9 deaths."}
    )
    _reviewed_match(client, tmp_path, provider)
    result = client.post(
        f"/player/matches/{MATCH_ID}/ask?lang=en", json={"question": "How many kills?"}
    ).json()
    assert result["ok"] is True and result["answer"]["answer"] == "You had 3 kills and 9 deaths."
    assert len(provider.calls) == 2 and "kills=160" in provider.calls[1][-1]["content"]
    history = client.get(f"/player/matches/{MATCH_ID}?lang=en").json()["questions"]
    assert history[0]["answer"] == result["answer"]["answer"]
    assert history[0]["counter_evidence"][0]["field"] == "kills"


def test_question_unknown_metric_is_rejected_and_never_cached(
    client: TestClient, tmp_path: Path
) -> None:
    provider = FakeLLM({"answer": "У вас 2 смерти."})
    _reviewed_match(client, tmp_path, provider)
    result = client.post(
        f"/player/matches/{MATCH_ID}/ask?lang=ru", json={"question": "Сколько смертей?"}
    ).json()
    assert result == {"ok": False, "code": "unverified"}
    assert len(provider.calls) == 2
    assert client.get(f"/player/matches/{MATCH_ID}?lang=ru").json()["questions"] == []


def test_legacy_review_is_hidden_until_regenerated_even_when_ai_is_off(
    client: TestClient, tmp_path: Path
) -> None:
    service = _reviewed_match(client, tmp_path, None)
    key = f"coach:match:{ME}:{MATCH_ID}:ru"
    legacy = {"hash": "old", "review": {"summary": "У вас 160 убийств."}}
    service.store.cache_set(key, legacy)
    coach = client.get(f"/player/matches/{MATCH_ID}?lang=ru").json()["coach"]
    assert coach == {"state": "off"}
    assert service.store.cache_get(key) == legacy
    service.llm = FakeLLM(GOOD_MATCH_REVIEW)
    assert client.get(f"/player/matches/{MATCH_ID}?lang=ru").json()["coach"] == {"state": "pending"}
    service.ai_jobs.run_pending(until=float("inf"))
    coach = client.get(f"/player/matches/{MATCH_ID}?lang=ru").json()["coach"]
    assert coach["state"] == "ready" and coach["review"]["summary"] == GOOD_MATCH_REVIEW["summary"]
    assert service.store.cache_get(key)["verification_version"] == COACH_VERSION


def test_legacy_questions_are_rechecked_on_read_without_provider_or_storage_deletion(
    client: TestClient, tmp_path: Path
) -> None:
    service = _reviewed_match(client, tmp_path, None)
    key = f"{ASK_CACHE_KEY}:{ME}:{MATCH_ID}"
    history = [
        {"question": "How many kills?", "answer": "You had 160 kills.", "lang": "en"},
        {"question": "How many deaths?", "answer": "You had 9 deaths.", "lang": "en"},
    ]
    service.store.cache_set(key, history)
    returned = client.get(f"/player/matches/{MATCH_ID}?lang=en").json()["questions"]
    assert len(returned) == 1 and returned[0]["answer"] == history[1]["answer"]
    assert returned[0]["counter_evidence"][0]["field"] == "kills"
    assert service.store.cache_get(key) == history
