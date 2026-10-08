"""Internal normalized state, source facts and findings; not raw provider JSON."""

from __future__ import annotations

from typing import Any, Literal, NotRequired, TypedDict

from app.finding_evidence import FindingEvidence, FindingField, RecordingCoverage


class NormalizedState(TypedDict):
    hero: str
    role: Literal["carry"]
    minute: int
    level: int
    gold: int
    items: list[str]
    hp_percent: int
    game_state: str
    team_status: str
    # Independent trackers add optional signals; missing signals are omitted.
    extra_context: dict[str, Any]


class MatchFacts(TypedDict):
    match_id: int
    sources: list[str]
    provenance: dict[FindingField, FindingEvidence | None]
    recording_coverage: RecordingCoverage | None
    clock_offset: int | None
    parsed: bool
    hero: str | None
    hero_id: int | None
    duration: int | None
    win: bool | None
    is_radiant: bool | None
    lane_role: int | None
    is_roaming: bool
    kills: int | None
    deaths: int | None
    assists: int | None
    last_hits: int | None
    denies: int | None
    gpm: int | None
    xpm: int | None
    level: int | None
    net_worth: int | None
    hero_damage: int | None
    tower_damage: int | None
    hero_healing: int | None
    team_kills: int | None
    kill_participation: float | None
    teamfight_participation: float | None
    lane_efficiency_pct: float | None
    obs_placed: int | None
    sen_placed: int | None
    camps_stacked: int | None
    rune_pickups: int | None
    stuns: float | None
    time_dead: int | None
    benchmarks: dict[str, float]
    lh_t: list[int | None]
    dn_t: list[int | None]
    gold_t: list[int | None]
    xp_t: list[int | None]
    # Source-specific event extensions are intentionally open at this boundary.
    deaths_log: list[dict[str, Any]]
    items_log: list[dict[str, Any]]
    buybacks: list[int]
    killed_by: dict[str, int]
    final_items: list[int | str]
    inventory: list[int | str]
    path: list[dict[str, Any]]
    wards: list[dict[str, Any]]
    lane_pos: list[list[int]]
    skill_upgrades: list[int]
    advice_log: list[dict[str, Any]]


class Finding(TypedDict):
    id: str
    params: dict[str, Any]
    evidence: list[FindingEvidence]
    kind: NotRequired[Literal["strength", "improve"]]
    section: NotRequired[str]
    severity: NotRequired[int]
    weight: NotRequired[float]
