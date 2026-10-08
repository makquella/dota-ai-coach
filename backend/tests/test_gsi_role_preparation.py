"""Actual metadata/store boundaries stay outside GSI and core memory owners."""

from __future__ import annotations

import sqlite3
import sys
import threading
from types import FrameType
from typing import Any

import pytest
from fastapi.testclient import TestClient
from test_gsi_snapshot import _packet

from app import gsi_state, player_store
from app.gsi_snapshot import GSIRegister
from app.live_role import set_role_setting
from app.match_memory import MATCH_MEMORY
from app.player_api import PLAYER_SERVICE
from app.player_service import PlayerService


@pytest.mark.parametrize("role", ["auto", "support"])
def test_real_sqlite_metadata_runs_outside_gsi_and_memory_owners(
    client: TestClient, role: str
) -> None:
    set_role_setting(role)
    calls: list[str] = []
    violations: list[str] = []
    original = threading.gettrace()

    def trace(frame: FrameType, event: str, _arg: Any) -> Any:
        if event == "call" and frame.f_code.co_filename == player_store.__file__:
            calls.append(frame.f_code.co_name)
            caller = frame.f_back
            while caller is not None:
                if caller.f_code is GSIRegister.update.__code__ or (
                    caller.f_code.co_name == "guarded"
                    and caller.f_locals.get("self") is MATCH_MEMORY
                ):
                    violations.append(frame.f_code.co_name)
                caller = caller.f_back
        return None

    threading.settrace(trace)
    try:
        response = client.post("/gsi", json=_packet())
    finally:
        threading.settrace(original)
    assert response.status_code == 200
    assert "primary_account_id" in calls and "cache_get" in calls
    assert violations == []
    assert response.json()["state"]["hero"] == "Juggernaut"
    overlay = client.get("/overlay/recommendation").json()
    assert overlay["hero_coverage"] == ("support" if role == "support" else "full")
    if role == "support":
        assert overlay["decision_point"] not in {"LANING_FARM_CHECK", "SAFE_FARMING", "ITEM_TIMING"}


def test_reset_can_finish_while_actual_role_metadata_lookup_is_paused(client: TestClient) -> None:
    # Keep one ASGI event loop for concurrent requests, as in the real server.
    # A sync SQLite lookup on that loop would block reset even without a lock.
    with client:
        _reset_during_role_lookup(client)


def _reset_during_role_lookup(client: TestClient) -> None:
    entered, release, reset_done = threading.Event(), threading.Event(), threading.Event()
    responses: dict[str, Any] = {}
    errors: list[Exception] = []
    original = threading.gettrace()

    def trace(frame: FrameType, event: str, _arg: Any) -> Any:
        if (
            event == "call"
            and frame.f_code is PlayerService.role_prior.__code__
            and frame.f_locals["hero"] == "Luna"
        ):
            sys.settrace(None)
            entered.set()
            assert release.wait(5)
        return None

    def write() -> None:
        try:
            responses["writer"] = client.post("/gsi", json=_packet("luna", 70))
        except Exception as error:  # noqa: BLE001 - capture real request failures
            errors.append(error)

    def reset() -> None:
        try:
            responses["reset"] = client.post("/session/reset")
        except Exception as error:  # noqa: BLE001 - capture real request failures
            errors.append(error)
        finally:
            reset_done.set()

    workers = [threading.Thread(target=write), threading.Thread(target=reset)]
    threading.settrace(trace)
    try:
        # Install tracing before the first request creates its reusable worker.
        assert client.post("/gsi", json=_packet()).status_code == 200
        workers[0].start()
        assert entered.wait(5)
        assert client.get("/state/current").json()["state"]["hero"] == "Juggernaut"
        assert client.get("/session/memory").json()["hero"] == "Juggernaut"
        workers[1].start()
        assert reset_done.wait(2)
        assert responses["reset"].status_code == 200
        assert client.get("/state/current").json()["state"] is None
        assert client.get("/session/memory").json()["hero"] is None
    finally:
        threading.settrace(original)
        release.set()
        for worker in workers:
            if worker.ident is not None:
                worker.join(5)
    assert not any(worker.is_alive() for worker in workers) and not errors
    assert responses["writer"].status_code == 200
    # The packet commits after reset once preparation finishes; arrival time
    # does not reserve a writer epoch or block reset.
    assert client.get("/state/current").json()["state"]["hero"] == "Luna"


def test_role_metadata_failure_occurs_before_any_new_memory_or_packet_commit(
    client: TestClient,
) -> None:
    assert client.post("/gsi", json=_packet()).status_code == 200
    previous = client.get("/gsi/debug/latest").json()
    memory = client.get("/session/memory").json()
    PLAYER_SERVICE.store.close()  # Actual SQLite failure, no replacement metadata method.
    with pytest.raises(sqlite3.ProgrammingError, match="closed database"):
        client.post("/gsi", json=_packet("luna", 70))
    assert client.get("/gsi/debug/latest").json() == previous
    assert client.get("/session/memory").json() == memory


@pytest.mark.parametrize(
    ("payload", "hero"),
    [
        ({"hero_name": "luna", "hero": {"name": "npc_dota_hero_juggernaut"}}, "Luna"),
        ({"hero": "phantom lancer"}, "Phantom Lancer"),
        ({"hero": {"name": "npc_dota_hero_nevermore"}}, "Shadow Fiend"),
        ({"hero_name": None, "hero": {"name": "npc_dota_hero_zuus"}}, "Zeus"),
        ({"hero_name": "", "hero": {"name": "npc_dota_hero_zuus"}}, "Unknown"),
        ({"hero": None}, "Unknown"),
        ({}, "Unknown"),
    ],
)
def test_preparation_and_actual_normalization_select_the_same_hero(
    payload: dict[str, Any], hero: str
) -> None:
    assert gsi_state.hero_from_gsi(payload) == hero
    assert gsi_state.normalize_gsi_payload(payload)["hero"] == hero
