"""Domain types and finding DTOs protect real producer and HTTP boundaries."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from match_fixtures import MATCH_ID, ME, FakeOpenDota, opendota_match
from pydantic import ValidationError
from test_coach_ai import _reviewed_match

from app.gsi_state import normalize_gsi_payload
from app.match_facts import facts_from_opendota, facts_from_timeline
from app.opendota import trim_match
from app.player_api import PLAYER_SERVICE
from app.player_contracts import FindingEvidenceResponse, FindingResponse, RecordingCoverageResponse


def test_native_source_inventory_values_keep_ids_and_names_and_drop_invalid_types() -> None:
    raw = opendota_match()
    raw["players"][0].update(
        {
            "item_0": 1,
            "item_1": "item_tango",
            "item_2": True,
            "item_3": None,
            "item_4": 1.5,
            "item_5": {"name": "item_blink"},
        }
    )
    facts = facts_from_opendota(trim_match(raw, ME))
    assert facts is not None and facts["inventory"] == [1, "item_tango"]
    assert facts_from_timeline({"final": {"inventory": ["item_tango", None, True, "item_blink"]}})[
        "inventory"
    ] == ["item_tango", "item_blink"]


def test_normalized_core_remains_identical_for_sparse_packet_and_unknown_signals() -> None:
    state = normalize_gsi_payload({"hero": {"name": "npc_dota_hero_luna"}})
    assert state["hero"] == "Luna" and state["role"] == "carry"
    assert state["minute"] == 0 and state["level"] == 1 and state["gold"] == 0
    assert state["items"] == [] and state["hp_percent"] == 100
    assert "last_hits" not in state["extra_context"]
    assert "enemy_units" not in state["extra_context"]


@pytest.mark.parametrize("language", ["uk", "en"])
def test_finding_and_coverage_dto_roundtrip_complete_real_http_review(
    client: TestClient, tmp_path: Path, language: str
) -> None:
    raw = opendota_match(good=False)
    raw["players"][0]["lh_t"][10] = 20
    service = PLAYER_SERVICE
    service.configure(tmp_path, client=FakeOpenDota(matches={MATCH_ID: raw}), auto_start=False)
    client.post("/player/link", json={"steam": str(ME)})
    service.fetch_match(MATCH_ID, request_parse=False)
    service.jobs.run_pending(until=float("inf"))
    response = client.get(f"/player/matches/{MATCH_ID}?lang={language}")
    assert response.status_code == 200 and response.json() == service.match_detail(
        MATCH_ID, language
    )
    analysis = response.json()["analysis"]
    row = next(f for f in analysis["evidence_findings"] if f["id"] == "lh10_low")
    assert row["params"]["lh10"] == 20 and row["evidence"][0]["value"] == 20
    assert FindingResponse.model_validate(row).model_dump(exclude_unset=True) == row
    for finding in analysis["improvements"] + analysis["strengths"]:
        assert FindingResponse.model_validate(finding).model_dump(exclude_unset=True) == finding


@pytest.mark.parametrize(
    "patch",
    [
        {"value": True},
        {"value": "0"},
        {"value": -1},
        {"value": 2**53},
        {"field": "sen_placed"},
        {"source": "opendota.lh_t"},
        {"observed_at": 600},
        {"coverage": {"start": 0, "end": 600, "gaps": [], "complete": True}},
    ],
)
def test_evidence_dto_rejects_invalid_values_and_cross_field_source(patch: dict[str, Any]) -> None:
    row = {
        "field": "obs_placed",
        "source": "opendota.obs_log",
        "precision": "log_count",
        "value": 0,
        "observed_at": None,
        "coverage": None,
    }
    with pytest.raises(ValidationError):
        FindingEvidenceResponse.model_validate({**row, **patch})


@pytest.mark.parametrize(
    "patch",
    [
        {"start": True},
        {"start": "0"},
        {"end": -1},
        {"gaps": [[30]]},
        {"gaps": [[60, 30]]},
        {"gaps": [[30, 700]], "complete": False},
        {"gaps": [[30, 60]]},
        {"start": 30},
    ],
)
def test_recording_dto_rejects_invalid_or_inconsistent_coverage(patch: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        RecordingCoverageResponse.model_validate(
            {"start": 0, "end": 600, "gaps": [], "complete": True, **patch}
        )


def test_finding_dto_preserves_legacy_unknown_extensions_without_inventing_evidence() -> None:
    wire = {
        "id": "legacy",
        "params": {"count": None},
        "title": "Keep",
        "future_extension": [0, None],
    }
    assert FindingResponse.model_validate(wire).model_dump(exclude_unset=True) == wire
    with pytest.raises(ValidationError):
        FindingResponse.model_validate({"id": "bad", "params": {}, "evidence": [True]})


def test_openapi_exposes_finding_and_recording_contracts(client: TestClient) -> None:
    models = client.get("/openapi.json").json()["components"]["schemas"]
    assert models["MatchAnalysis"]["properties"]["improvements"]["anyOf"][0]["items"][
        "$ref"
    ].endswith("/FindingResponse")
    assert models["FindingResponse"]["properties"]["evidence"]["items"]["$ref"].endswith(
        "/FindingEvidenceResponse"
    )
    assert models["FindingEvidenceResponse"]["properties"]["value"]["type"] == "integer"
    assert models["FindingEvidenceResponse"]["additionalProperties"] is False


@pytest.mark.parametrize("invalid", [False, True])
def test_mypy_checks_actual_producer_return_types_and_finding_keys(
    tmp_path: Path, invalid: bool
) -> None:
    source = """from app.domain_contracts import Finding
from app.gsi_state import normalize_gsi_payload
from app.match_facts import facts_from_timeline

state = normalize_gsi_payload({})
facts = facts_from_timeline({})
finding: Finding = {"id": "lane_deaths", "params": {"count": 2}, "evidence": []}
known_minute: int = state["minute"]
unknown_kills: int | None = facts["kills"]
unknown_series: list[int | None] = facts["lh_t"]
"""
    if invalid:
        source += """state["hp_percent"] = None
facts["kills"] = "5"
facts["gpmm"] = 500
facts["lh_t"] = [None, "0"]
finding["evidence"] = [True]
"""
    target = tmp_path / "domain_types.py"
    target.write_text(source)
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "mypy",
            "--follow-imports=silent",
            "--strict",
            "--no-incremental",
            str(target),
        ],
        cwd=Path(__file__).parents[1],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if invalid:
        assert result.returncode == 1 and result.stdout.count(": error:") == 5, (
            result.stdout + result.stderr
        )
        assert 'TypedDict "MatchFacts" has no key "gpmm"' in result.stdout
    else:
        assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize(
    "params, identifier",
    [({"obs": True}, "wards_low"), ({"obs": 2}, "wards_low"), ({"obs": 0}, "lane_deaths")],
)
def test_finding_dto_binds_measurement_to_its_own_id_and_params(
    params: dict[str, Any], identifier: str
) -> None:
    row = {
        "field": "obs_placed",
        "source": "opendota.obs_log",
        "precision": "log_count",
        "value": 0,
        "observed_at": None,
        "coverage": None,
    }
    with pytest.raises(ValidationError):
        FindingResponse.model_validate({"id": identifier, "params": params, "evidence": [row]})


def test_invalid_cached_finding_is_rebuilt_from_sources_without_losing_note(
    client: TestClient, tmp_path: Path
) -> None:
    service = _reviewed_match(client, tmp_path, None)
    client.post(f"/player/matches/{MATCH_ID}/note", json={"note": "Keep"})
    bad = copy.deepcopy(service.store.get_match(ME, MATCH_ID)["analysis"])
    bad["evidence_findings"][0]["evidence"][0]["source"] = "unknown"
    service.store.upsert_match(ME, MATCH_ID, source="opendota", analysis=bad)
    response = client.get(f"/player/matches/{MATCH_ID}?lang=en")
    assert response.status_code == 200
    body = response.json()
    assert body["summary"]["note"] == "Keep" and body["coach"] == {"state": "off"}
    assert body["analysis"]["evidence_findings"][0]["evidence"][0]["source"] != "unknown"
    assert service.store.get_match(ME, MATCH_ID)["analysis"] != bad


def test_invalid_backup_finding_fails_before_any_database_mutation(
    client: TestClient, tmp_path: Path
) -> None:
    service = _reviewed_match(client, tmp_path, None)
    backup = client.get("/player/backup").json()
    before = service.store.backup_snapshot()
    row = backup["tables"]["matches"][0]
    analysis = json.loads(row["analysis_json"])
    analysis["evidence_findings"][0]["evidence"][0]["source"] = "unknown"
    row["analysis_json"] = json.dumps(analysis)
    response = client.post("/player/backup", json=backup)
    assert response.status_code == 400 and response.json()["code"] == "not_backup"
    assert service.store.backup_snapshot() == before
