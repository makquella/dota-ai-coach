"""Farm totals bind to their own fields through real review/question/cache paths."""

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
        "You had 3 last hits.",
        "У вас 160 денаев.",
        "LH: 390.",
        "Denies were 2.",
        "You had -160 last hits.",
        "DN: 3.5.",
        "Anti-Mage had 160 last hits.",
        "Your team had 160 last hits.",
        "У союзника 160 добиваний.",
        "160 last hits at 10:00.",
        "160 last hits in lane.",
        "160 last hits in the last 10 minutes.",
        "160 last hits per minute.",
        "У вас 160 добиваний за первые 10 минут.",
    ],
)
def test_other_metrics_nested_data_and_scopes_cannot_prove_farm_totals(text: str) -> None:
    facts = {
        "hero": "Juggernaut",
        "match_farm": {"last_hits": 160, "denies": 3},
        "gpm": 390,
        "at": "10:00",
        "lane": {"last_hits": 3, "denies": 160},
        "enemy": "Anti-Mage",
    }
    assert FactChecker(json.dumps(facts), []).problems(text)


@pytest.mark.parametrize(
    "text",
    [
        "You had 160 last hits and 3 denies.",
        "Last hits were 160.",
        "Last-hits: 160.",
        "LH: 160, DN: 3.",
        "У вас 160 добиваний и 3 деная.",
        "Добивания: 160, денаев было 3.",
        "160 добитых крипов.",
        "0.16k last hits.",
    ],
)
def test_correct_total_nouns_and_abbreviations_are_kept(text: str) -> None:
    assert (
        FactChecker(json.dumps({"match_farm": {"last_hits": 160, "denies": 3}}), []).problems(text)
        == []
    )


@pytest.mark.parametrize("value", [None, True, "160", -1, 160.0, float("nan"), float("inf"), 2**53])
def test_invalid_farm_counter_remains_unknown_without_a_number_inventory_bypass(
    value: object,
) -> None:
    facts = match_facts({"analysis": {"headline": {"last_hits": value, "gpm": 160}}})
    assert facts is not None and facts["match_farm"] == facts["match_farm_evidence"] == {}
    assert "last_hits" not in facts
    assert FactChecker(json.dumps(facts), []).problems("160 last hits.")
    assert FactChecker(json.dumps(facts), []).problems("0 denies.")


def test_zero_direct_callers_and_empty_ledger_preserve_the_evidence_boundary() -> None:
    facts = match_facts({"analysis": {"headline": {"last_hits": 0}}})
    assert facts is not None and facts["match_farm"] == {"last_hits": 0}
    assert FactChecker(json.dumps(facts), []).problems("0 last hits.") == []
    assert facts["match_farm_evidence"]["last_hits"] == {
        "source": "analysis.headline",
        "field": "last_hits",
        "observed_at": None,
        "precision": "reported_total",
        "value": 0,
    }
    assert (
        FactChecker(json.dumps({"last_hits": 160, "denies": 3}), []).problems("LH: 160, DN: 3.")
        == []
    )
    unknown = {"match_farm": {}, "last_hits": 160, "lane": {"last_hits": 160}}
    assert FactChecker(json.dumps(unknown), []).problems("160 last hits.")


@pytest.mark.parametrize("language", ["ru", "en"])
def test_review_scrubs_farm_swaps_attaches_own_evidence_and_preserves_future_goals(
    client: TestClient, tmp_path: Path, language: str
) -> None:
    review = copy.deepcopy(GOOD_MATCH_REVIEW)
    review["summary"] += " You had 3 last hits. У вас 160 денаев."
    review["strengths"] = ["LH: 160, DN: 3."]
    review["next_game"] = ["Aim for 390 last hits."]
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
            "precision": "reported_total",
            "value": value,
        }
        for field, value in (("last_hits", 160), ("denies", 3))
    ]
    assert returned["review"]["farm_evidence"] == expected
    facts = json.loads(provider.calls[0][1]["content"])
    assert facts["match_farm_evidence"]["last_hits"] == expected[0]
    assert "match_farm" in provider.calls[0][0]["content"]
    assert (
        service.store.cache_get(f"coach:match:{ME}:{MATCH_ID}:{language}")["verification_version"]
        == COACH_VERSION
    )


def test_question_retries_swap_and_persists_farm_refs(client: TestClient, tmp_path: Path) -> None:
    provider = FakeLLM(
        {"answer": "You had 3 last hits."}, {"answer": "160 last hits and 3 denies."}
    )
    service = _reviewed_match(client, tmp_path, provider)
    returned = client.post(
        f"/player/matches/{MATCH_ID}/ask?lang=en", json={"question": "How was my farm?"}
    ).json()
    assert returned["ok"] and returned["answer"]["answer"] == "160 last hits and 3 denies."
    assert len(provider.calls) == 2 and "last_hits=3" in provider.calls[1][-1]["content"]
    stored = service.store.cache_get(f"{ASK_CACHE_KEY}:{ME}:{MATCH_ID}")
    assert stored[0]["farm_evidence"] == returned["answer"]["farm_evidence"]
    assert [row["field"] for row in stored[0]["farm_evidence"]] == ["last_hits", "denies"]


def test_unverified_farm_answer_is_not_saved(client: TestClient, tmp_path: Path) -> None:
    provider = FakeLLM({"answer": "160 denies."})
    service = _reviewed_match(client, tmp_path, provider)
    result = client.post(
        f"/player/matches/{MATCH_ID}/ask?lang=en", json={"question": "Denies?"}
    ).json()
    assert result == {"ok": False, "code": "unverified"} and len(provider.calls) == 2
    assert service.store.cache_get(f"{ASK_CACHE_KEY}:{ME}:{MATCH_ID}") is None


def test_upgrade_hides_v3_review_and_rechecks_saved_questions_without_provider_or_deletion(
    client: TestClient, tmp_path: Path
) -> None:
    service = _reviewed_match(client, tmp_path, None)
    coach_key = f"coach:match:{ME}:{MATCH_ID}:en"
    cached = {"hash": "old", "verification_version": 3, "review": {"summary": "3 last hits."}}
    service.store.cache_set(coach_key, cached)
    ask_key = f"{ASK_CACHE_KEY}:{ME}:{MATCH_ID}"
    history = [
        {"question": "LH?", "answer": "3 last hits. Your last hits were 160.", "lang": "en"},
        {"question": "DN?", "answer": "160 denies.", "lang": "en"},
    ]
    service.store.cache_set(ask_key, history)
    body = client.get(f"/player/matches/{MATCH_ID}?lang=en").json()
    assert body["coach"] == {"state": "off"}
    assert (
        len(body["questions"]) == 1 and body["questions"][0]["answer"] == "Your last hits were 160."
    )
    assert body["questions"][0]["farm_evidence"][0]["value"] == 160
    assert (
        service.store.cache_get(coach_key) == cached and service.store.cache_get(ask_key) == history
    )
    service.llm = FakeLLM(GOOD_MATCH_REVIEW)
    assert client.get(f"/player/matches/{MATCH_ID}?lang=en").json()["coach"] == {"state": "pending"}
    service.ai_jobs.run_pending(until=float("inf"))
    ready = client.get(f"/player/matches/{MATCH_ID}?lang=en").json()["coach"]
    assert ready["state"] == "ready" and ready["review"]["farm_evidence"][0]["value"] == 160


def _slice_facts() -> dict[str, object]:
    return {
        "hero": "Juggernaut",
        "match_farm": {"last_hits": 160, "denies": 3},
        "match_farm_at_10": {
            "hero": "Juggernaut",
            "enemy": "Anti-Mage",
            "points": [{"minute": 10, "lh": 36, "dn": 2, "enemy_lh": 65, "enemy_dn": 4}],
        },
        "other": [160, 3, 36, 65, 2, 4, "Anti-Mage", "Axe", "5:00"],
    }


@pytest.mark.parametrize(
    "text",
    [
        "You had 36 last hits at 10:00.",
        "LH: 36, DN: 2 by minute 10.",
        "К 10:00 у вас 36 добиваний против 65 у Anti-Mage.",
        "36 добиваний к 10:00 против 65 у Anti-Mage.",
        "36 last hits versus 65 for Anti-Mage at 10:00.",
    ],
)
def test_supported_10_minute_samples_bind_player_and_named_opponent(text: str) -> None:
    facts = _slice_facts()
    assert FactChecker(json.dumps(facts), []).problems(text) == []
    del facts["match_farm"]
    assert FactChecker(json.dumps(facts), []).problems(text) == []


@pytest.mark.parametrize(
    "text",
    [
        "160 last hits at 10:00.",
        "36 denies at 10:00.",
        "3 denies at 10:00.",
        "65 добиваний к 10:00 против 36 у Anti-Mage.",
        "36 добиваний к 10:00 против 36 у Anti-Mage.",
        "36 добиваний к 10:00 против 65 у Axe.",
        "36 last hits at 5:00.",
        "36 last hits at 5:00 and 10:00.",
        "36 last hits in lane at 10:00.",
        "Anti-Mage had 36 last hits at 10:00.",
    ],
)
def test_total_metric_subject_comparison_or_timestamp_swaps_cannot_use_a_10_minute_sample(
    text: str,
) -> None:
    facts = _slice_facts()
    assert FactChecker(json.dumps(facts), []).problems(text)
    del facts["match_farm"]
    assert FactChecker(json.dumps(facts), []).problems(text)


@pytest.mark.parametrize(
    "points",
    [
        [],
        [{"minute": 5, "lh": 36}],
        [{"minute": 10.0, "lh": 36}],
        [{"minute": 10, "lh": True}],
        [{"minute": 10, "lh": 36}, {"minute": 10, "lh": 36}],
    ],
)
def test_missing_invalid_or_ambiguous_10_minute_samples_remain_unknown(
    points: list[dict[str, object]],
) -> None:
    facts = match_facts({"analysis": {"headline": {"last_hits": 36}, "lane": {"points": points}}})
    assert facts is not None
    assert FactChecker(json.dumps(facts), []).problems("36 last hits at 10:00.")
    assert facts["match_farm_at_10_evidence"] == []


def test_peer_sample_keeps_its_own_source_without_inventing_denies_or_a_lane() -> None:
    facts = match_facts(
        {
            "analysis": {
                "headline": {"hero": "Juggernaut", "last_hits": 160},
                "peers": {
                    "me": {"lh_10": 36.0},
                    "peers": [{"hero": "Anti-Mage", "enemy": True, "metrics": {"lh_10": 65.0}}],
                },
            }
        }
    )
    assert facts is not None
    rows = facts["match_farm_at_10_evidence"]
    assert [(r["source"], r["subject"], r["value"]) for r in rows] == [
        ("analysis.peers.me", "player", 36),
        ("analysis.peers.peers[0].metrics", "opponent", 65),
    ]
    assert all(r["observed_at"] == 600 and r["precision"] == "reported_sample" for r in rows)
    checker = FactChecker(json.dumps(facts), [])
    assert checker.problems("36 last hits versus 65 for Anti-Mage at 10:00.") == []
    assert checker.problems("0 denies at 10:00.")
    assert checker.problems("36 last hits in lane at 10:00.")


def test_question_retries_a_named_10_minute_comparison_swap_and_saves_sample_refs(
    client: TestClient,
    tmp_path: Path,
) -> None:
    provider = FakeLLM(
        {"answer": "К 10:00 у вас 65 добиваний против 36 у Anti-Mage."},
        {"answer": "К 10:00 у вас 36 добиваний против 65 у Anti-Mage."},
    )
    service = _reviewed_match(client, tmp_path, provider)
    result = client.post(
        f"/player/matches/{MATCH_ID}/ask?lang=ru", json={"question": "Фарм к 10:00?"}
    ).json()
    assert result["ok"] and len(provider.calls) == 2
    refs = result["answer"]["farm_slice_evidence"]
    assert [(r["subject"], r["value"]) for r in refs] == [("player", 36), ("opponent", 65)]
    assert (
        service.store.cache_get(f"{ASK_CACHE_KEY}:{ME}:{MATCH_ID}")[0]["farm_slice_evidence"]
        == refs
    )
