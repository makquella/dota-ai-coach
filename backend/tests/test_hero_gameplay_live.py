"""Real raw-GSI → owned episodes → decision/scheduler → localized overlay/recording."""

from __future__ import annotations

import gzip
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.gsi_state import normalize_gsi_payload
from app.hero_gameplay import MAX_SHOWS_PER_RULE, RULE_REPEAT_SECONDS, HeroGameplay
from app.hero_gameplay_texts import GAMEPLAY_VERSION, RULES, GameplayRule

HERO_KEYS = {"Sven": "sven", "Juggernaut": "juggernaut", "Terrorblade": "terrorblade"}


def packet(rule: GameplayRule, *, clock: int = 600) -> dict[str, Any]:
    health = 650 if rule.gate == "recovery" else 1000
    abilities = [rule.ability]
    if rule.gate == "meta_pair":
        abilities.append("terrorblade_metamorphosis")
    result: dict[str, Any] = {
        "map": {
            "matchid": "9876543210",
            "clock_time": clock,
            "game_time": clock,
            "game_state": "DOTA_GAMERULES_STATE_GAME_IN_PROGRESS",
            "paused": False,
        },
        "player": {
            "steamid": "76561198000000009",
            "team_name": "radiant",
            "deaths": 0,
            "gold": 0,
            "last_hits": 70,
        },
        "hero": {
            "name": f"npc_dota_hero_{HERO_KEYS[rule.hero]}",
            "level": 12,
            "alive": True,
            "health": health,
            "max_health": 1000,
            "health_percent": health // 10,
            "mana": 700,
            "max_mana": 700,
            "mana_percent": 100,
            **{
                flag: False
                for flag in ("stunned", "hexed", "silenced", "muted", "disarmed", "smoked")
            },
            "aghanims_scepter": rule.gate == "scepter",
            "aghanims_shard": rule.gate == "shard",
        },
        "abilities": {
            f"ability{i}": {
                "name": name,
                "level": 1,
                "cooldown": 0,
                "can_cast": True,
                "ability_active": True,
            }
            for i, name in enumerate(abilities)
        },
        "items": {"slot0": {"name": "item_power_treads"}},
    }
    if rule.gate == "teleport":
        result["items"]["teleport0"] = {"name": "item_tpscroll", "can_cast": True, "cooldown": 0}
    if rule.gate == "slash_item":
        result["items"]["slot1"] = {"name": "item_black_king_bar", "can_cast": True, "cooldown": 0}
    return result


def read(client: TestClient, value: dict[str, Any], *, lang: str = "en") -> dict[str, Any]:
    assert client.post("/gsi", json=value).status_code == 200
    response = client.get(f"/overlay/recommendation?lang={lang}")
    assert response.status_code == 200
    return response.json()


def use_clock(monkeypatch: pytest.MonkeyPatch, value: dict[str, Any]) -> None:
    # GSI clocks advance without waiting minutes in tests. Keep the scheduler's
    # wall clock in sync too: its UX gate intentionally also limits real time.
    monkeypatch.setattr(
        "app.advice_scheduler._utcnow",
        lambda now=None: (
            now
            or datetime(2026, 10, 14, tzinfo=UTC) + timedelta(seconds=value["map"]["clock_time"])
        ),
    )


@pytest.mark.parametrize("rule", RULES, ids=lambda rule: rule.id)
def test_every_preparation_variant_reaches_the_real_overlay_and_uk_copy(
    client: TestClient, rule: GameplayRule, repo_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    value = packet(rule)
    use_clock(monkeypatch, value)
    response = read(client, value)
    if (response.get("hero_gameplay") or {}).get("rule_id") != rule.id:
        # Related lessons share an ability. Let the first lesson consume its
        # episode; the other waits for the real 90-second hero spacing.
        assert response["decision_point"] == "HERO_GAMEPLAY"
        for clock in range(601, 691):
            value["map"].update(clock_time=clock, game_time=clock)
            assert client.post("/gsi", json=value).status_code == 200
        response = client.get("/overlay/recommendation").json()
    assert response["decision_point"] == "HERO_GAMEPLAY"
    assert response["new_advice"] is True
    assert response["llm_used"] is False
    assert response["advice_mode"] == "coaching"
    assert response["recommendation"]["priority"] == "low"
    assert response["recommendation"]["action"] == rule.action
    assert response["recommendation"]["reason"] == rule.reason
    context = response["hero_gameplay"]
    assert context["rule_id"] == rule.id and context["version"] == GAMEPLAY_VERSION
    assert context["observed"]["ability"]["raw_name"] == rule.ability
    assert "76561198000000009" not in json.dumps(context)
    localized = client.get("/overlay/recommendation?lang=uk").json()
    assert localized["recommendation"]["action"] == rule.action_uk
    assert localized["recommendation"]["reason"] == rule.reason_uk
    assert localized["new_advice"] is False
    # Sources and field names are actual audited Valve snapshots, not invented
    # mechanics or a claim that the designed target interaction ran in a lobby.
    key = HERO_KEYS[rule.hero]
    catalog = json.loads((repo_root / f"data/hero_advice_research/catalogs/{key}.json").read_text())
    source = json.loads((repo_root / f"data/hero_advice_research/sources/{key}.json").read_text())
    assert set(rule.evidence) <= {m["id"] for m in catalog["mechanics"]}
    assert rule.ability in source["hero"]["abilities"]
    assert len(rule.action) <= 100 and len(rule.reason) <= 180
    assert len(rule.action_uk) <= 100 and len(rule.reason_uk) <= 180


@pytest.mark.parametrize(
    "damage",
    [
        "absent_abilities",
        "unlearned",
        "absent_castability",
        "castability_false",
        "castability_string",
        "inactive_ability",
        "absent_active_flag",
        "cooldown",
        "absent_cooldown",
        "absent_health",
        "boolean_health",
        "absent_status",
        "silenced",
        "paused",
        "absent_pause",
        "early",
        "dead",
    ],
)
def test_unknown_invalid_or_unavailable_own_signals_never_enable_preparation(
    client: TestClient, damage: str
) -> None:
    value = packet(RULES[2])  # Sven's ultimate; no target data required.
    ability = value["abilities"]["ability0"]
    if damage == "absent_abilities":
        value.pop("abilities")
    elif damage == "unlearned":
        ability["level"] = 0
    elif damage == "absent_castability":
        ability.pop("can_cast")  # ability_active=True must not stand in for it.
    elif damage == "castability_false":
        ability["can_cast"] = False
    elif damage == "castability_string":
        ability["can_cast"] = "true"
    elif damage == "inactive_ability":
        ability["ability_active"] = False
    elif damage == "absent_active_flag":
        ability.pop("ability_active")
    elif damage == "cooldown":
        ability["cooldown"] = 30
    elif damage == "absent_cooldown":
        ability.pop("cooldown")
    elif damage == "absent_health":
        value["hero"].pop("health")
    elif damage == "boolean_health":
        value["hero"]["health"] = True
    elif damage == "absent_status":
        value["hero"].pop("silenced")
    elif damage == "silenced":
        value["hero"]["silenced"] = True
    elif damage == "paused":
        value["map"]["paused"] = True
    elif damage == "absent_pause":
        value["map"].pop("paused")
    elif damage == "early":
        value["map"]["clock_time"] = 30
    elif damage == "dead":
        value["hero"]["alive"] = False
        value["player"]["deaths"] = 1
    response = read(client, value)
    assert response["decision_point"] != "HERO_GAMEPLAY"
    assert not response.get("hero_gameplay")


@pytest.mark.parametrize(
    "rule",
    [r for r in RULES if r.gate in {"scepter", "shard", "meta_pair", "teleport", "slash_item"}],
    ids=lambda rule: rule.id,
)
def test_upgrade_combo_and_inventory_requirements_are_observed(
    client: TestClient, rule: GameplayRule
) -> None:
    value = packet(rule)
    if rule.gate in {"scepter", "shard"}:
        value["hero"].pop(f"aghanims_{rule.gate}")
    elif rule.gate == "meta_pair":
        value["abilities"]["ability1"]["can_cast"] = False
    elif rule.gate == "teleport":
        value["items"].pop("teleport0")
    else:
        value["items"]["slot1"]["cooldown"] = 45
    response = read(client, value)
    assert (response.get("hero_gameplay") or {}).get("rule_id") != rule.id


def test_actual_upgrade_acquisition_enables_the_new_variant(client: TestClient) -> None:
    value = packet(RULES[0])
    value["hero"]["aghanims_scepter"] = False
    assert read(client, value)["decision_point"] != "HERO_GAMEPLAY"
    value["map"].update(clock_time=601, game_time=601)
    value["hero"]["aghanims_scepter"] = True
    response = read(client, value)
    assert response["hero_gameplay"]["rule_id"] == RULES[0].id


@pytest.mark.parametrize("change", ["missing_castability", "not_castable", "backpack"])
def test_omni_item_lesson_requires_an_explicitly_usable_inventory_item(
    client: TestClient, change: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    rule = next(r for r in RULES if r.gate == "slash_item")
    value = packet(rule)
    use_clock(monkeypatch, value)
    if change == "missing_castability":
        value["items"]["slot1"].pop("can_cast")
    elif change == "not_castable":
        value["items"]["slot1"]["can_cast"] = False
    else:
        value["items"]["slot6"] = value["items"].pop("slot1")
    first = read(client, value)
    assert first["hero_gameplay"]["rule_id"] == "juggernaut.omni_isolation.prepare"
    for clock in range(601, 691):
        value["map"].update(clock_time=clock, game_time=clock)
        assert client.post("/gsi", json=value).status_code == 200
    response = client.get("/overlay/recommendation").json()
    assert not response.get("hero_gameplay")


@pytest.mark.parametrize(
    "cancel", ["spent", "missing", "unknown_status", "damage", "death", "paused"]
)
def test_stale_preparation_is_removed_and_urgent_survival_can_interrupt(
    client: TestClient, cancel: str
) -> None:
    value = packet(RULES[2])
    first = read(client, value)
    assert first["new_advice"] is True
    value["map"].update(clock_time=601, game_time=601)
    if cancel == "spent":
        value["abilities"]["ability0"].update(cooldown=90, can_cast=False)
    elif cancel == "missing":
        value.pop("abilities")
    elif cancel == "unknown_status":
        value["hero"].pop("hexed")
    elif cancel == "damage":
        value["hero"].update(health=200, health_percent=20)
    elif cancel == "death":
        value["hero"].update(alive=False, health=0, health_percent=0)
        value["player"]["deaths"] = 1
    else:
        value["map"]["paused"] = True
    response = read(client, value)
    assert response.get("hero_gameplay") is None
    assert (response.get("recommendation") or {}).get("action") != RULES[2].action
    if cancel == "damage":
        assert response["decision_point"] == "LOW_HP" and response["new_advice"] is True


def test_same_episode_is_not_repeated_and_a_later_ready_episode_can_show(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    value = packet(RULES[2])
    use_clock(monkeypatch, value)
    first = read(client, value)
    for clock in range(601, 910):
        value["map"].update(clock_time=clock, game_time=clock)
        response = read(client, value)
        assert not (response.get("new_advice") and response.get("hero_gameplay"))
    value["map"].update(clock_time=910, game_time=910)
    value["abilities"]["ability0"].update(cooldown=30, can_cast=False)
    read(client, value)
    value["map"].update(clock_time=911, game_time=911)
    value["abilities"]["ability0"].update(cooldown=0, can_cast=True)
    response = read(client, value)
    # A normal farm card can precede the restored ability. Preparation does
    # not interrupt its spacing; the queued new episode must survive the wait.
    if not response["new_advice"]:
        for clock in range(912, 962):
            value["map"].update(clock_time=clock, game_time=clock)
            assert client.post("/gsi", json=value).status_code == 200
        response = client.get("/overlay/recommendation").json()
    assert response["new_advice"] is True and response["hero_gameplay"]
    assert response["hero_gameplay"]["episode_id"] != first["hero_gameplay"]["episode_id"]


def test_hero_change_reset_and_gsi_gap_do_not_keep_old_preparation(client: TestClient) -> None:
    first = read(client, packet(RULES[2]))
    assert first["hero_gameplay"]
    unknown = packet(RULES[2], clock=620)
    unknown.pop("abilities")
    assert not read(client, unknown).get("hero_gameplay")
    value = packet(next(r for r in RULES if r.id == "terrorblade.sunder_target.prepare"), clock=621)
    response = read(client, value)
    assert (response.get("hero_gameplay") or {}).get("rule_id") != RULES[2].id
    assert client.post("/session/reset").status_code == 200
    reset = read(client, packet(RULES[2], clock=622))
    assert reset["new_advice"] is True and reset["hero_gameplay"]["rule_id"] == RULES[2].id


def test_match_download_contains_only_the_shown_rule_and_own_evidence(client: TestClient) -> None:
    assert client.post("/settings/advice", json={"match_records": True}).status_code == 200
    first = read(client, packet(RULES[2]))
    assert first["hero_gameplay"]
    client.get("/overlay/recommendation")
    record = client.get("/match-records").json()["records"][0]
    download = client.get(f"/match-records/{record['id']}")
    assert download.status_code == 200
    lines = [json.loads(line) for line in gzip.decompress(download.content).splitlines()]
    advice = [line for line in lines if line["k"] == "advice" and line.get("hero_gameplay")]
    assert len(advice) == 1
    assert advice[0]["hero_gameplay"] == first["hero_gameplay"]
    assert "76561198000000009" not in json.dumps(lines)


def test_concurrent_overlay_polls_deliver_the_owned_episode_only_once(client: TestClient) -> None:
    assert client.post("/gsi", json=packet(RULES[2])).status_code == 200
    with ThreadPoolExecutor(max_workers=2) as pool:
        replies = list(pool.map(lambda _: client.get("/overlay/recommendation"), range(2)))
    assert all(reply.status_code == 200 for reply in replies)
    bodies = [reply.json() for reply in replies]
    assert sum(bool(body.get("new_advice")) for body in bodies) == 1
    assert {body["hero_gameplay"]["episode_id"] for body in bodies} == {1}
    assert {body["advice_count"] for body in bodies} == {1}


def test_hero_preparation_works_when_the_player_selects_a_support_role(client: TestClient) -> None:
    assert client.post("/settings/advice", json={"role": "support"}).status_code == 200
    response = read(client, packet(RULES[2]))
    assert response["decision_point"] == "HERO_GAMEPLAY" and response["new_advice"]
    assert response["hero_gameplay"]["rule_id"] == RULES[2].id


def test_each_preparation_tip_is_shown_at_most_twice_a_match() -> None:
    rule = RULES[2]
    gameplay = HeroGameplay()
    shown = 0
    for cycle in range(6):
        start = 600 + cycle * (RULE_REPEAT_SECONDS + 10)
        spent = packet(rule, clock=start)
        spent["abilities"]["ability0"].update(cooldown=30, can_cast=False)
        gameplay.observe(normalize_gsi_payload(spent))
        for clock in range(start + 1, start + 4):
            state = normalize_gsi_payload(packet(rule, clock=clock))
            gameplay.observe(state)
            context = gameplay.context(state)
            if context is not None:
                gameplay.shown(context, clock)
                shown += 1
    assert shown == MAX_SHOWS_PER_RULE


def test_a_lane_farm_check_comes_before_a_preparation_tip(client: TestClient) -> None:
    value = packet(RULES[2])
    value["player"]["last_hits"] = 5  # far behind the lane pace at 10 minutes
    response = read(client, value)
    assert response["decision_point"] == "LANING_FARM_CHECK"
    assert not response.get("hero_gameplay")
