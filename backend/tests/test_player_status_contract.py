"""Player polling DTO against real HTTP, SQLite and queue/provider lifecycles."""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from match_fixtures import MATCH_ID, ME, ME_STEAM64, FakeOpenDota
from pydantic import ValidationError
from test_gsi_snapshot import _packet

from app.opendota import OpenDotaError
from app.player_api import PLAYER_SERVICE
from app.player_contracts import PlayerStatusResponse


@pytest.mark.parametrize("source", ["unlinked", "manual", "gsi"])
def test_idle_linked_and_gsi_status_preserve_real_wire_fields(
    client: TestClient, source: str
) -> None:
    if source == "manual":
        assert client.post("/player/link", json={"steam": str(ME)}).status_code == 200
    elif source == "gsi":
        packet = _packet()
        packet["player"]["steamid"] = ME_STEAM64
        assert client.post("/gsi", json=packet).status_code == 200
    response = client.get("/player")
    assert response.status_code == 200
    body = response.json()
    assert body == PLAYER_SERVICE.status()
    assert body["linked"] is (source != "unlinked")
    assert body["account_id"] == (None if source == "unlinked" else ME)
    assert body["source"] == (None if source == "unlinked" else source)
    assert body["sync"] == {"state": "idle", "at": None, "error": None, "error_code": None}
    assert body["pending_jobs"] == body["matches"] == 0
    assert body["opendota"] is False and isinstance(body["ai"]["configured"], bool)
    assert {
        "player",
        "detected",
        "live_match",
        "last_review",
        "today",
        "goals",
        "tilt",
    } <= body.keys()


def test_queue_reports_queued_running_and_done_with_real_thread_and_provider(
    client: TestClient, tmp_path: Path
) -> None:
    entered, release = threading.Event(), threading.Event()

    class PausedOpenDota(FakeOpenDota):
        def player(self, account_id: int) -> dict[str, Any]:
            entered.set()
            assert release.wait(5)
            return super().player(account_id)

    service = PLAYER_SERVICE
    service.configure(tmp_path, client=PausedOpenDota(), auto_start=False)
    assert client.post("/player/link", json={"steam": str(ME)}).status_code == 200
    queued = client.get("/player").json()
    assert queued["sync"]["state"] == "queued" and queued["pending_jobs"] == 1
    errors: list[Exception] = []

    def run() -> None:
        try:
            service.jobs.run_pending(until=float("inf"))
        except Exception as error:  # noqa: BLE001 - inspect real worker failure
            errors.append(error)

    worker = threading.Thread(target=run)
    worker.start()
    try:
        assert entered.wait(5)
        running = client.get("/player").json()
        assert running["sync"]["state"] == "running" and running["pending_jobs"] == 1
        assert running["sync"]["at"] is None and "fetched" not in running["sync"]
    finally:
        service.jobs.request_stop()
        release.set()
        worker.join(5)
    assert not worker.is_alive() and not errors
    done = client.get("/player").json()
    assert done["sync"]["state"] == "done" and done["sync"]["fetched"] == 0
    assert isinstance(done["sync"]["at"], str) and done["pending_jobs"] == 0
    assert done["player"]["persona_name"] == "Me"


def test_provider_failure_status_preserves_error_code_and_nullable_fields(
    client: TestClient, tmp_path: Path
) -> None:
    class FailingOpenDota(FakeOpenDota):
        def player(self, account_id: int) -> dict[str, Any]:
            raise OpenDotaError("rate_limited", "Remote limit")

    service = PLAYER_SERVICE
    service.configure(tmp_path, client=FailingOpenDota(), auto_start=False)
    assert client.post("/player/link", json={"steam": str(ME)}).status_code == 200
    service.jobs.run_pending(until=float("inf"))
    body = client.get("/player").json()
    assert body["sync"]["state"] == "error" and body["sync"]["error_code"] == "rate_limited"
    assert body["sync"]["error"] == "Remote limit" and "fetched" not in body["sync"]
    assert body["account_id"] == ME and body["pending_jobs"] == 0


def test_status_keeps_sqlite_profile_match_count_and_existing_extensions(
    client: TestClient,
) -> None:
    service = PLAYER_SERVICE
    service.store.set_primary(ME, source="manual")
    service.store.upsert_player(ME, source="opendota", persona_name="Тест / Test", rank_tier=None)
    service.store.upsert_match(
        ME, MATCH_ID, source="gsi", fields={"hero_id": 8}, timeline={"match_id": MATCH_ID}
    )
    before = service.status()
    body = client.get("/player").json()
    assert body == before
    assert body["matches"] == 1 and body["player"]["persona_name"] == "Тест / Test"
    assert body["player"]["rank_tier"] is None


@pytest.mark.parametrize(
    "path,value",
    [
        ("linked", "false"),
        ("account_id", True),
        ("matches", "0"),
        ("pending_jobs", -1),
        ("ai.configured", 1),
        ("sync.at", 123),
        ("sync.fetched", 1.5),
    ],
)
def test_core_contract_rejects_coercion_and_invalid_counts_from_a_real_status(
    client: TestClient, path: str, value: object
) -> None:
    body = client.get("/player").json()
    target = body
    keys = path.split(".")
    for key in keys[:-1]:
        target = target[key]
    target[keys[-1]] = value
    with pytest.raises(ValidationError):
        PlayerStatusResponse.model_validate(body)


def test_absent_and_null_fields_and_future_extensions_remain_distinct(client: TestClient) -> None:
    body = client.get("/player").json()
    body["extension"] = {"keep": True}
    body["sync"]["state"] = "future_state"
    body["sync"]["future_detail"] = {"keep": True}
    assert PlayerStatusResponse.model_validate(body).model_dump(exclude_unset=True) == body
    body["sync"]["fetched"] = None
    assert PlayerStatusResponse.model_validate(body).model_dump(exclude_unset=True) == body


def test_openapi_describes_the_status_sync_and_ai_response_models(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    response = schema["paths"]["/player"]["get"]["responses"]["200"]["content"]["application/json"][
        "schema"
    ]
    assert response == {"$ref": "#/components/schemas/PlayerStatusResponse"}
    models = schema["components"]["schemas"]
    fields = models["PlayerStatusResponse"]["properties"]
    assert fields["linked"]["type"] == "boolean"
    assert fields["pending_jobs"]["minimum"] == 0 and fields["pending_jobs"]["maximum"] == 2**53 - 1
    assert fields["sync"]["$ref"] == "#/components/schemas/PlayerSyncResponse"
    assert models["PlayerAIResponse"]["properties"]["configured"]["type"] == "boolean"
    assert "fetched" not in models["PlayerSyncResponse"]["required"]
