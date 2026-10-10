"""The validated HTTP boundary preserves real SQLite reviews and unknowns."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from match_fixtures import MATCH_ID, ME, FakeOpenDota, opendota_match
from pydantic import ValidationError
from test_coach_ai import GOOD_MATCH_REVIEW, FakeLLM, _reviewed_match

from app.match_facts import facts_from_timeline
from app.player_api import PLAYER_SERVICE
from app.player_contracts import CombatCounters, MatchDetailResponse
from app.post_match_analysis import analyze_match


@pytest.mark.parametrize("parsed", [True, False])
@pytest.mark.parametrize("lang", ["uk", "en"])
def test_response_validation_preserves_complete_review_and_note(
    client: TestClient, tmp_path: Path, parsed: bool, lang: str
) -> None:
    provider = FakeOpenDota(matches={MATCH_ID: opendota_match(parsed=parsed)})
    service = PLAYER_SERVICE
    service.configure(tmp_path, client=provider, auto_start=False)
    assert client.post("/player/link", json={"steam": str(ME)}).status_code == 200
    service.fetch_match(MATCH_ID, request_parse=False)
    service.jobs.run_pending(until=float("inf"))
    note = "Перевірити ранній фарм / Check early farm"
    assert client.post(f"/player/matches/{MATCH_ID}/note", json={"note": note}).status_code == 200

    response = client.get(f"/player/matches/{MATCH_ID}?lang={lang}")
    assert response.status_code == 200
    body = response.json()
    assert body == service.match_detail(MATCH_ID, lang)
    assert body["summary"]["note"] == note
    assert body["analysis"]["parsed"] is parsed
    assert body["analysis"]["headline"]["kills"] == 11
    assert len(body["scoreboard"]) == 10
    assert body["analysis"]["sections"] and body["analysis"]["strengths"]
    assert {"coach", "focus", "baseline", "best_on_hero", "questions", "repeats"} <= body.keys()


@pytest.mark.parametrize("totals", [{"kills": 0, "assists": 5}, {"deaths": 4, "assists": 9}])
def test_gsi_only_review_keeps_partial_totals_and_zero_over_http(
    client: TestClient, totals: dict[str, int]
) -> None:
    service = PLAYER_SERVICE
    service.store.set_primary(ME, source="gsi")
    timeline = {
        "match_id": MATCH_ID,
        "hero": "Juggernaut",
        "hero_id": 8,
        "duration": 1800,
        "final": totals,
    }
    analysis = analyze_match(facts_from_timeline(timeline))
    service.store.upsert_match(
        ME,
        MATCH_ID,
        source="gsi",
        fields={"hero_id": 8, "duration": 1800, **totals},
        timeline=timeline,
        analysis=analysis,
    )
    response = client.get(f"/player/matches/{MATCH_ID}")
    assert response.status_code == 200
    body = response.json()
    expected = {key: totals.get(key) for key in ("kills", "deaths", "assists")}
    assert {key: body["analysis"]["headline"][key] for key in expected} == expected
    assert {key: body["summary"][key] for key in expected} == expected
    assert body["sources"] == ["gsi"] and body["loading"] is False
    assert body == service.match_detail(MATCH_ID, "en")


def test_loading_and_missing_match_keep_distinct_wire_shapes(
    client: TestClient, tmp_path: Path
) -> None:
    service = PLAYER_SERVICE
    service.configure(tmp_path, client=FakeOpenDota(), auto_start=False)
    service.store.set_primary(ME, source="manual")
    service.store.upsert_match(ME, MATCH_ID, source="opendota", parse_status="pending")
    response = client.get(f"/player/matches/{MATCH_ID}")
    assert response.status_code == 200
    assert response.json()["analysis"] is None and response.json()["loading"] is True
    assert response.json() == service.match_detail(MATCH_ID, "en")
    missing = client.get(f"/player/matches/{MATCH_ID + 1}")
    assert missing.status_code == 404
    assert missing.json() == {"status": "error", "code": "match_not_found"}


def test_coach_and_question_evidence_survive_response_validation(
    client: TestClient, tmp_path: Path
) -> None:
    provider = FakeLLM(GOOD_MATCH_REVIEW, {"answer": "You had 3 kills and 9 deaths."})
    service = _reviewed_match(client, tmp_path, provider)
    assert client.get(f"/player/matches/{MATCH_ID}?lang=uk").status_code == 200
    service.ai_jobs.run_pending(until=float("inf"))
    answer = client.post(
        f"/player/matches/{MATCH_ID}/ask?lang=en", json={"question": "How many kills?"}
    )
    assert answer.status_code == 200 and answer.json()["ok"] is True
    body = client.get(f"/player/matches/{MATCH_ID}?lang=uk").json()
    assert body == service.match_detail(MATCH_ID, "uk")
    assert body["coach"]["review"]["counter_evidence"][0]["observed_at"] is None
    assert body["questions"][0]["counter_evidence"]
    assert body["questions"][0]["answer"] == answer.json()["answer"]["answer"]


@pytest.mark.parametrize("value", [True, "2", 2.5, -1, 2**53])
def test_declared_counters_do_not_coerce_invalid_values(value: Any) -> None:
    for field in ("kills", "deaths", "assists"):
        with pytest.raises(ValidationError):
            CombatCounters.model_validate({field: value})


def test_optional_legacy_counters_are_not_invented_during_serialization() -> None:
    wire = {
        "match_id": 0,
        "summary": {"kills": 0, "note": "keep"},
        "sources": None,
        "parse_status": "",
        "analysis": {"headline": {"deaths": None, "score": 40}, "legacy_extension": [1, None]},
        "loading": False,
        "future_extension": {"value": None},
    }
    assert MatchDetailResponse.model_validate(wire).model_dump(exclude_unset=True) == wire


def test_openapi_documents_success_missing_match_and_nullable_integer_counters(
    client: TestClient,
) -> None:
    schema = client.get("/openapi.json").json()
    route = schema["paths"]["/player/matches/{match_id}"]["get"]
    for code, name in (("200", "MatchDetailResponse"), ("404", "MatchNotFoundResponse")):
        assert route["responses"][code]["content"]["application/json"]["schema"]["$ref"] == (
            f"#/components/schemas/{name}"
        )
    models = schema["components"]["schemas"]
    for field in ("kills", "deaths", "assists"):
        types = models["CombatCounters"]["properties"][field]["anyOf"]
        assert types == [{"type": "integer", "maximum": 2**53 - 1, "minimum": 0}, {"type": "null"}]
    assert models["MatchDetailResponse"]["additionalProperties"] is True
    assert models["MatchNotFoundResponse"]["properties"]["code"]["const"] == "match_not_found"
