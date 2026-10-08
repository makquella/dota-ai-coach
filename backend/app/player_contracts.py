"""Validated player status/list/detail cores; extensions stay intact."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt

CombatCount = Annotated[StrictInt, Field(ge=0, le=2**53 - 1)]
StoredMatchId = Annotated[StrictInt, Field(ge=0, le=2**63 - 1)]
Count = CombatCount
StoredAccountId = StoredMatchId
Percent = Annotated[StrictInt, Field(ge=0, le=100)]


class ExtensibleResponse(BaseModel):
    """Validate declared fields without dropping existing review sections."""

    model_config = ConfigDict(extra="allow", strict=True)


class CombatCounters(ExtensibleResponse):
    """Missing counters are unknown; zero remains a measured total."""

    kills: CombatCount | None = None
    deaths: CombatCount | None = None
    assists: CombatCount | None = None


class MatchAnalysis(ExtensibleResponse):
    headline: CombatCounters


class MatchDetailResponse(ExtensibleResponse):
    match_id: StoredMatchId
    summary: CombatCounters
    sources: list[str] | None
    parse_status: str
    analysis: MatchAnalysis | None
    loading: bool


class MatchNotFoundResponse(BaseModel):
    status: Literal["error"]
    code: Literal["match_not_found"]


class PlayerSyncResponse(ExtensibleResponse):
    state: str
    at: str | None
    error: str | None
    error_code: str | None
    fetched: Count | None = None


class PlayerAIResponse(ExtensibleResponse):
    configured: bool


class PlayerStatusResponse(ExtensibleResponse):
    linked: bool
    account_id: StoredAccountId | None
    source: str | None
    opendota: bool
    sync: PlayerSyncResponse
    matches: Count
    pending_jobs: Count
    ai: PlayerAIResponse
    opendota_key: bool


class MatchListItem(CombatCounters):
    match_id: StoredMatchId
    hero_id: Count | None = None
    hero: str | None = None
    win: bool | None = None
    sources: list[str]
    parse_status: str | None
    has_analysis: bool
    has_timeline: bool
    items: list[str] | None = None
    note: str | None = None


class MatchListStats(ExtensibleResponse):
    games: Count
    wins: Count
    winrate: Percent | None
    avg_score: StrictInt | None


class MatchHeroCount(ExtensibleResponse):
    hero_id: Count
    hero: str | None
    games: Count


class MatchListFilters(ExtensibleResponse):
    hero_id: Count | None
    win: bool | None
    sort: str
    ascending: bool


class SkippedModesResponse(ExtensibleResponse):
    count: Count
    turbo: Count
    of: Count


class MatchListResponse(ExtensibleResponse):
    linked: bool
    items: list[MatchListItem]
    total: Count
    stats: MatchListStats | None = None
    heroes: list[MatchHeroCount] | None = None
    filters: MatchListFilters | None = None
    sync: PlayerSyncResponse | None = None
    skipped: SkippedModesResponse | None = None
