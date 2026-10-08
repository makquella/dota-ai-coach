"""Three finding groups retain measurement semantics from source to HTTP/AI/UI."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from match_fixtures import MATCH_ID, ME, opendota_match
from test_coach_ai import GOOD_MATCH_REVIEW, FakeLLM, _reviewed_match

from app.analysis_texts import render_analysis
from app.coach_review import COACH_VERSION, FactChecker, match_facts
from app.finding_evidence import analysis_evidence, recording_coverage, validated_evidence
from app.match_facts import facts_from_opendota, facts_from_timeline, merge_facts
from app.opendota import trim_match
from app.player_service import ASK_CACHE_KEY
from app.post_match_analysis import analyze_match


def _timeline(*, complete: bool = True) -> dict[str, Any]:
    return {
        "match_id": MATCH_ID,
        "hero": "Crystal Maiden",
        "duration": 1800,
        "obs_placed": 0,
        "deaths": [{"t": 180}, {"t": 420}],
        "samples": [
            {"t": t, "lh": t // 30, "dn": 0, "gpm": 180}
            for t in range(0 if complete else 900, 1801, 15)
        ],
        "final": {"last_hits": 30, "kills": 0, "deaths": 2, "assists": 8, "gpm": 180},
    }


def _facts() -> dict[str, Any]:
    raw = opendota_match(good=False)
    raw["players"][0]["lh_t"][10] = 20
    facts = facts_from_opendota(trim_match(raw, ME))
    assert facts is not None
    return facts


def _ledger() -> dict[str, Any]:
    facts = _facts()
    facts["provenance"]["obs_placed"]["value"] = 2
    facts["provenance"]["sen_placed"]["value"] = 7
    rows = list(facts["provenance"].values())
    return {
        "hero": "Juggernaut",
        "match_totals": {"kills": 3, "deaths": 9, "assists": 6},
        "finding_evidence": {"test": rows},
        "other_numbers": [2, 7, 10, 36, 65],
    }


def test_parsed_ward_logs_override_aggregate_and_preserve_known_zero() -> None:
    raw = opendota_match(good=False)
    me = raw["players"][0]
    me.update(
        {
            "obs_placed": 99,
            "sen_placed": 77,
            "obs_log": [],
            "sen_log": [{"time": 30}, {"time": 40}],
            "last_hits": 0,
        }
    )
    facts = facts_from_opendota(trim_match(raw, ME))
    assert facts is not None and (facts["obs_placed"], facts["sen_placed"]) == (0, 2)
    analysis = render_analysis(analyze_match(facts), "ru")
    finding = next(f for f in analysis["improvements"] if f["id"] == "wards_low")
    assert finding["evidence"][0] == {
        "field": "obs_placed",
        "source": "opendota.obs_log",
        "precision": "log_count",
        "value": 0,
        "observed_at": None,
        "coverage": None,
    }
    assert analysis_evidence(analysis)["wards_low"] == finding["evidence"]


def test_missing_logs_do_not_invent_zero_events() -> None:
    trimmed = trim_match(opendota_match(good=False), ME)
    for player in trimmed["players"]:
        player.pop("kills_log", None)
    trimmed["players"][0].pop("obs_placed", None)
    facts = facts_from_opendota(trimmed)
    assert facts is not None
    assert facts["provenance"]["obs_placed"] is None
    assert facts["provenance"]["lane_deaths"] is None


def test_exact_lh10_and_death_log_are_attached_and_not_a_claim_about_gold() -> None:
    analysis = render_analysis(analyze_match(_facts()), "en")
    rows = analysis_evidence(analysis)
    assert rows["lh10_low"][0]["value"] == 20
    assert rows["lh10_low"][0]["observed_at"] == 600
    assert rows["lane_deaths"][0]["value"] == 2
    assert rows["lane_deaths"][0]["source"] == "opendota.kills_log"
    text = next(f["text"] for f in analysis["improvements"] if f["id"] == "lh10_low")
    assert "gold" not in text


def test_late_recording_and_gaps_stay_unknown_and_do_not_score_vision() -> None:
    timeline = _timeline(complete=False)
    facts = facts_from_timeline(timeline)
    assert facts["lh_t"][:15] == [None] * 15
    analysis = analyze_match(facts)
    assert analysis["recording_coverage"] == {
        "start": 900,
        "end": 1800,
        "gaps": [],
        "complete": False,
    }
    assert "vision" not in analysis["sections"]
    assert not any(
        f["id"] in {"lh10_low", "lh10_great", "wards_low", "wards_high"}
        for f in analysis["improvements"] + analysis["strengths"]
    )
    timeline["samples"] = [{"t": 0, "lh": 0}, {"t": 60, "lh": 10}, {"t": 240, "lh": 20}]
    facts = facts_from_timeline(timeline)
    assert facts["lh_t"][:5] == [0, 10, None, None, 20]
    assert recording_coverage(timeline)["gaps"] == [[0, 60], [60, 240]]


def test_complete_recording_labels_inventory_estimate_and_unknown_sentries() -> None:
    facts = facts_from_timeline(_timeline())
    analysis = render_analysis(analyze_match(facts), "en")
    finding = next(f for f in analysis["improvements"] if f["id"] == "wards_low")
    assert finding["evidence"][0]["precision"] == "inventory_estimate"
    assert finding["evidence"][0]["coverage"]["complete"] is True
    facts["obs_placed"] = 20
    facts["provenance"]["obs_placed"]["value"] = 20
    finding = next(
        f
        for f in render_analysis(analyze_match(facts), "en")["strengths"]
        if f["id"] == "wards_high"
    )
    assert "— sentry" in finding["text"]
    assert [r["field"] for r in finding["evidence"]] == ["obs_placed"]


def test_carried_gsi_sample_does_not_license_exact_lh10_finding() -> None:
    timeline = _timeline()
    timeline["samples"] = [s for s in timeline["samples"] if s["t"] != 600]
    timeline["final"]["last_hits"] = 160
    facts = facts_from_timeline(timeline)
    assert facts["provenance"]["lh10"]["observed_at"] == 585
    assert facts["provenance"]["lh10"]["precision"] == "carried_sample"
    assert not any(
        f["id"] in {"lh10_low", "lh10_great"}
        for f in analyze_match(facts)["improvements"] + analyze_match(facts)["strengths"]
    )


def test_merge_keeps_ward_source_and_uses_gsi_only_for_selected_facts() -> None:
    opendota = _facts()
    gsi = facts_from_timeline(_timeline())
    gsi["obs_placed"] = 20
    gsi["provenance"]["obs_placed"]["value"] = 20
    merged = merge_facts(opendota, gsi)
    assert (
        merged["obs_placed"] == 0
        and merged["provenance"]["obs_placed"]["source"] == "opendota.obs_placed"
    )
    opendota["obs_placed"] = None
    opendota["provenance"]["obs_placed"] = None
    merged = merge_facts(opendota, gsi)
    assert (
        merged["obs_placed"] == 20
        and merged["provenance"]["obs_placed"]["source"] == "gsi.inventory_changes"
    )


@pytest.mark.parametrize(
    "change",
    [
        {"field": []},
        {"source": {}},
        {"value": True},
        {"value": 1.5},
        {"observed_at": 600.0},
        {"observed_at": True},
        {"source": "gsi.samples"},
        {"coverage": {"start": 0, "end": 600, "gaps": [[0, 60]], "complete": True}},
    ],
)
def test_malformed_measurements_are_rejected(change: dict[str, Any]) -> None:
    row = _facts()["provenance"]["lh10"]
    assert validated_evidence({**row, **change}) is None


def test_evidence_is_detached_and_param_mismatches_and_duplicates_are_unknown() -> None:
    analysis = analyze_match(facts_from_timeline(_timeline()))
    finding = next(f for f in analysis["improvements"] if f["id"] == "wards_low")
    rows = analysis_evidence(analysis)
    rows["wards_low"][0]["coverage"]["gaps"].append([30, 60])
    assert finding["evidence"][0]["coverage"]["gaps"] == []
    finding["params"]["obs"] = True
    assert analysis_evidence(analysis)["wards_low"] == []
    analysis["evidence_findings"].append(copy.deepcopy(finding))
    assert "wards_low" not in analysis_evidence(analysis)


@pytest.mark.parametrize(
    "text",
    [
        "2 observer wards and 7 sentry wards.",
        "У вас 2 обсервер-варда и 7 сентри.",
        "Recorded 2 deaths before minute 10.",
        "Зафиксировано 2 смерти до 10-й минуты.",
    ],
)
def test_valid_source_bound_claims_are_kept(text: str) -> None:
    assert FactChecker(json.dumps(_ledger()), []).problems(text) == []


@pytest.mark.parametrize(
    "text",
    [
        "7 observer wards.",
        "2 sentry wards.",
        "3 observer wards.",
        "2 wards.",
        "2 варда.",
        "Anti-Mage placed 2 observer wards.",
        "2 observer wards before minute 10.",
        "Recorded 9 deaths before minute 10.",
        "2 deaths before minute 10.",
        "Recorded 2 deaths before minute 5.",
        "Recorded 2 deaths before minute 10 for Anti-Mage.",
        "Recorded 2 deaths before minute 10 and 2 kills.",
    ],
)
def test_metric_subject_and_time_swaps_fail_even_for_allowed_small_numbers(text: str) -> None:
    assert FactChecker(json.dumps(_ledger()), []).problems(text)


def test_inventory_estimate_requires_qualifier_and_complete_recording() -> None:
    row = facts_from_timeline(_timeline())["provenance"]["obs_placed"]
    checker = FactChecker(json.dumps({"finding_evidence": {"wards_low": [row]}}), [])
    assert checker.problems("Estimated 0 observer wards from inventory changes.") == []
    assert checker.problems("0 observer wards.")
    row["coverage"]["complete"] = False
    assert FactChecker(json.dumps({"finding_evidence": {"wards_low": [row]}}), []).problems(
        "Estimated 0 observer wards."
    )


def test_http_review_and_saved_question_use_backend_finding_evidence(
    client: TestClient, tmp_path: Path
) -> None:
    answer = {
        **GOOD_MATCH_REVIEW,
        "strengths": ["Recorded 2 deaths before minute 10.", "7 observer wards."],
    }
    llm = FakeLLM(answer)
    service = _reviewed_match(client, tmp_path, llm)
    client.get(f"/player/matches/{MATCH_ID}?lang=en")
    service.ai_jobs.run_pending(until=float("inf"))
    detail = client.get(f"/player/matches/{MATCH_ID}?lang=en").json()
    review = detail["coach"]["review"]
    assert review["strengths"] == ["Recorded 2 deaths before minute 10."]
    assert any(
        r["field"] == "lane_deaths" and r["source"] == "opendota.kills_log"
        for r in review["finding_evidence"]
    )
    prompt = json.loads(llm.calls[0][1]["content"])
    assert prompt["finding_evidence"]["lane_deaths"][0]["value"] == 2
    key = f"{ASK_CACHE_KEY}:{ME}:{MATCH_ID}"
    service.store.cache_set(
        key,
        [
            {
                "answer": "Recorded 2 deaths before minute 10. 7 observer wards.",
                "question": "Why?",
                "lang": "en",
                "at": "old",
            }
        ],
    )
    calls = len(llm.calls)
    questions = client.get(f"/player/matches/{MATCH_ID}?lang=en").json()["questions"]
    assert questions[0]["answer"] == "Recorded 2 deaths before minute 10."
    assert questions[0]["finding_evidence"] == review["finding_evidence"]
    assert len(llm.calls) == calls
    assert "7 observer" in service.store.cache_get(key)[0]["answer"]
    assert COACH_VERSION == 5


def test_future_ward_and_death_goals_keep_existing_policy() -> None:
    result, _, _, _ = FactChecker(json.dumps(_ledger()), []).scrub(
        {"next_game": ["Place 3 observer wards.", "Не больше 2 смертей до 10-й минуты."]}
    )
    assert result["next_game"] == ["Place 3 observer wards.", "Не больше 2 смертей до 10-й минуты."]


def test_lh10_finding_fills_ai_sample_when_lane_and_peers_are_absent() -> None:
    analysis = render_analysis(analyze_match(_facts()), "en")
    analysis.pop("lane", None)
    analysis.pop("peers", None)
    facts = match_facts({"analysis": analysis})
    assert FactChecker(json.dumps(facts), []).problems("20 last hits at 10:00.") == []
    assert FactChecker(json.dumps(facts), []).problems("65 last hits at 10:00.")


def test_v4_cache_is_hidden_offline_without_deleting_saved_ward_answer(
    client: TestClient, tmp_path: Path
) -> None:
    service = _reviewed_match(client, tmp_path, None)
    coach_key = f"coach:match:{ME}:{MATCH_ID}:en"
    cached = {"hash": "old", "verification_version": 4, "review": {"summary": "7 observer wards."}}
    service.store.cache_set(coach_key, cached)
    ask_key = f"{ASK_CACHE_KEY}:{ME}:{MATCH_ID}"
    history = [
        {
            "question": "Wards?",
            "answer": "7 observer wards. Recorded 2 deaths before minute 10.",
            "lang": "en",
        }
    ]
    service.store.cache_set(ask_key, history)
    body = client.get(f"/player/matches/{MATCH_ID}?lang=en").json()
    assert body["coach"] == {"state": "off"}
    assert body["questions"][0]["answer"] == "Recorded 2 deaths before minute 10."
    assert service.store.cache_get(coach_key) == cached
    assert service.store.cache_get(ask_key) == history
