"""Actual HTTP/thread/provider/file interleavings at live hint ownership."""

from __future__ import annotations

import sys
import threading
from pathlib import Path
from types import CodeType, FrameType
from typing import Any

import pytest
from fastapi.testclient import TestClient
from test_live_tracker_snapshot import _seen_packet, _snapshot
from test_match_memory_ownership import _paused_operation

from app import main, map_hints, player_store
from app.gold_tips import GoldTips
from app.live_hints import GoldHintInputs, LiveHintInputs
from app.map_hints import RoleTips
from app.match_memory import MATCH_MEMORY, MatchMemory
from app.player_service import PlayerService
from app.skill_tips import SkillTips


def _skill_packet(clock: int = 230, hero: str = "juggernaut") -> dict[str, Any]:
    packet = _seen_packet(hero, clock=clock)
    packet["hero"]["level"] = 1
    packet["abilities"] = {"ability0": {"name": f"{hero}_spell", "level": 0, "ultimate": False}}
    packet["items"] = {"slot0": {"name": "item_quelling_blade"}}
    return packet


def _ready(client: TestClient) -> None:
    assert client.post("/settings/advice", json={"role": "carry"}).status_code == 200
    for clock in (190, 230):
        assert client.post("/gsi", json=_skill_packet(clock)).status_code == 200


@pytest.mark.parametrize("operation", ["reset", "live"])
@pytest.mark.parametrize(
    "pause", [GoldTips.tip.__code__, SkillTips.tip.__code__, RoleTips.observe_level.__code__]
)
def test_real_tip_mutations_serialize_with_http_writes(
    client: TestClient, pause: CodeType, operation: str
) -> None:
    _ready(client)
    results: dict[str, Any] = {}
    errors: list[Exception] = []
    done = threading.Event()

    def read() -> None:
        try:
            results["read"] = client.get("/overlay/recommendation?lang=en")
        except Exception as error:  # noqa: BLE001 - inspect actual HTTP failure
            errors.append(error)

    def write() -> None:
        try:
            results["write"] = (
                client.post("/session/reset")
                if operation == "reset"
                else client.post("/gsi", json=_skill_packet(hero="luna"))
            )
        except Exception as error:  # noqa: BLE001 - inspect actual HTTP failure
            errors.append(error)
        finally:
            done.set()

    watch = (
        main.reset_session.__code__ if operation == "reset" else MatchMemory.observe_state.__code__
    )
    workers = [threading.Thread(target=read), threading.Thread(target=write)]
    with _paused_operation(pause, watch) as (entered, watched, release):
        workers[0].start()
        try:
            assert entered.wait(5)
            workers[1].start()
            assert watched.wait(5) and not done.wait(0.1)
        finally:
            release.set()
            for worker in workers:
                if worker.ident is not None:
                    worker.join(5)
    assert not any(worker.is_alive() for worker in workers) and not errors
    assert results["read"].status_code == results["write"].status_code == 200
    assert results["read"].json()["map_hint"]["id"] == "skill-point@1"
    assert client.get("/session/memory").json()["hero"] == (
        None if operation == "reset" else "Luna"
    )


def test_two_real_overlay_requests_share_one_tip_owner(client: TestClient) -> None:
    _ready(client)
    results: list[Any] = []
    errors: list[Exception] = []
    done = threading.Event()

    def read(second: bool) -> None:
        try:
            results.append(client.get("/overlay/recommendation?lang=en"))
        except Exception as error:  # noqa: BLE001 - inspect actual HTTP failure
            errors.append(error)
        finally:
            if second:
                done.set()

    workers = [threading.Thread(target=read, args=(second,)) for second in (False, True)]
    # Watch entry to the second HTTP handler: it already needs an owned enemy
    # read before reaching hint capture, and waits for the first renderer.
    with _paused_operation(SkillTips.tip.__code__, main.overlay_recommendation.__code__) as (
        entered,
        watched,
        release,
    ):
        workers[0].start()
        try:
            assert entered.wait(5)
            watched.clear()
            workers[1].start()
            assert watched.wait(5) and not done.wait(0.1)
        finally:
            release.set()
            for worker in workers:
                if worker.ident is not None:
                    worker.join(5)
    assert not any(worker.is_alive() for worker in workers) and not errors
    assert len(results) == 2 and all(response.status_code == 200 for response in results)
    hints = [response.json()["map_hint"] for response in results]
    assert hints[0] == hints[1] and hints[0]["id"] == "skill-point@1"


@pytest.mark.parametrize("operation", ["reset", "live"])
def test_stale_hint_preparation_does_not_mutate_new_memory(
    client: TestClient, operation: str
) -> None:
    _ready(client)
    entered, release = threading.Event(), threading.Event()
    results: list[Any] = []
    errors: list[Exception] = []
    tips: list[str] = []
    original = threading.gettrace()

    def trace(frame: FrameType, event: str, _arg: Any) -> Any:
        if (
            event == "call"
            and frame.f_code is PlayerService.skill_build.__code__
            and frame.f_locals["hero"] == "Juggernaut"
        ):
            entered.set()
            assert release.wait(5)
        if event == "call" and frame.f_code in (
            GoldTips.tip.__code__,
            SkillTips.tip.__code__,
            RoleTips.observe_level.__code__,
        ):
            tips.append(frame.f_code.co_name)
        return None

    def read() -> None:
        try:
            results.append(client.get("/overlay/recommendation?lang=en"))
        except Exception as error:  # noqa: BLE001 - inspect actual HTTP failure
            errors.append(error)

    threading.settrace(trace)
    worker = threading.Thread(target=read)
    try:
        worker.start()
        assert entered.wait(5)
        write = (
            client.post("/session/reset")
            if operation == "reset"
            else client.post("/gsi", json=_skill_packet(hero="luna"))
        )
        assert write.status_code == 200  # metadata prep holds no memory owner
        assert client.get("/session/memory").json()["hero"] == (
            None if operation == "reset" else "Luna"
        )
    finally:
        threading.settrace(original)
        release.set()
        worker.join(5)
    assert not worker.is_alive() and not errors
    assert len(results) == 1 and results[0].status_code == 200
    response = results[0].json()
    assert (
        "map_hint" not in response and "skill_bar" not in response and "live_role" not in response
    )
    assert tips == []
    if operation == "reset":
        _ready(client)
    else:
        assert client.post("/gsi", json=_skill_packet(250, hero="luna")).status_code == 200
    assert client.get("/overlay/recommendation?lang=en").json()["map_hint"]["id"] == "skill-point@1"


@pytest.mark.parametrize("role", ["carry", "support"])
@pytest.mark.parametrize("map_enabled", [False, True])
def test_actual_hint_metadata_store_and_files_run_outside_memory_ownership(
    client: TestClient, role: str, map_enabled: bool
) -> None:
    _ready(client)
    client.post("/settings/advice", json={"role": role, "map_hints": map_enabled})
    calls: list[str] = []
    violations: list[str] = []
    original = threading.gettrace()
    watched = {
        getattr(PlayerService, name).__code__
        for name in (
            "role_prior",
            "skill_build",
            "key_item",
            "save_item",
            "next_item",
            "start_items",
            "lane_records",
        )
    }

    def trace(frame: FrameType, event: str, _arg: Any) -> Any:
        if event == "call" and (
            frame.f_code in watched
            or frame.f_code.co_filename == player_store.__file__
            or frame.f_code is Path.read_text.__code__
        ):
            calls.append(frame.f_code.co_name)
            caller = frame.f_back
            while caller is not None:
                if (
                    caller.f_code.co_name == "guarded"
                    and caller.f_locals.get("self") is MATCH_MEMORY
                ):
                    violations.append(frame.f_code.co_name)
                caller = caller.f_back
        return None

    map_hints.timers.cache_clear()
    threading.settrace(trace)
    try:
        response = client.get("/overlay/recommendation?lang=uk")
    finally:
        threading.settrace(original)
        map_hints.timers.cache_clear()
    assert response.status_code == 200 and response.json()["map_hint"]["id"] == "skill-point@1"
    assert {"role_prior", "skill_build", "primary_account_id", "cache_get", "read_text"} <= set(
        calls
    )
    assert violations == []


def test_tip_exception_releases_owner_for_real_http_reset(client: TestClient) -> None:
    _ready(client)
    packet = _skill_packet(1000)
    packet["player"]["gold"] = 2000
    assert client.post("/gsi", json=packet).status_code == 200
    state = client.get("/state/current").json()["state"]
    inputs = LiveHintInputs(
        role={"role": "carry"},
        gold=GoldHintInputs(next_item={"key": "bad"}),
        map_enabled=True,
        carry_advisor=True,
    )
    with pytest.raises(KeyError, match="name"):
        MATCH_MEMORY.live_hints(state, state["extra_context"], _snapshot(1000), inputs, "en")
    results: list[Any] = []
    worker = threading.Thread(target=lambda: results.append(client.post("/session/reset")))
    worker.start()
    worker.join(5)
    assert not worker.is_alive() and len(results) == 1 and results[0].status_code == 200
    assert client.get("/session/memory").json()["hero"] is None


def test_direct_hint_facade_warms_cold_timer_file_before_ownership(client: TestClient) -> None:
    _ready(client)
    state = client.get("/state/current").json()["state"]
    trackers = _snapshot()
    inputs = LiveHintInputs(
        role={"role": "carry"}, gold=GoldHintInputs(), map_enabled=True, carry_advisor=True
    )
    reads: list[bool] = []
    original = sys.gettrace()

    def trace(frame: FrameType, event: str, _arg: Any) -> Any:
        if (
            event == "call"
            and frame.f_code is Path.read_text.__code__
            and frame.f_locals["self"] == map_hints.TIMERS_PATH
        ):
            owned = False
            caller = frame.f_back
            while caller is not None:
                owned |= (
                    caller.f_code.co_name == "guarded"
                    and caller.f_locals.get("self") is MATCH_MEMORY
                )
                caller = caller.f_back
            reads.append(owned)
        return None

    map_hints.timers.cache_clear()
    sys.settrace(trace)
    try:
        response = MATCH_MEMORY.live_hints(state, state["extra_context"], trackers, inputs, "en")
        assert response["map_hint"]["id"] == "skill-point@1" and reads == [False]
    finally:
        sys.settrace(original)
        map_hints.timers.cache_clear()
