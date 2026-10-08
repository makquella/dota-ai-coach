"""Validated player status/list/detail/progress/profile cores; preserve extensions."""

from __future__ import annotations

from typing import Annotated, Any, Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictFloat,
    StrictInt,
    ValidationError,
    model_validator,
)

from app.finding_evidence import (
    FINDING_FIELDS,
    PARAMS,
    FindingField,
    Precision,
    count,
    validated_evidence,
)

CombatCount = Annotated[StrictInt, Field(ge=0, le=2**53 - 1)]
StoredMatchId = Annotated[StrictInt, Field(ge=0, le=2**63 - 1)]
Count = CombatCount
StoredAccountId = StoredMatchId
Percent = Annotated[StrictInt, Field(ge=0, le=100)]
SignedCount = Annotated[StrictInt, Field(ge=-(2**53 - 1), le=2**53 - 1)]
Hours = Annotated[StrictFloat, Field(ge=0, allow_inf_nan=False)]


class ExtensibleResponse(BaseModel):
    """Validate declared fields without dropping existing review sections."""

    model_config = ConfigDict(extra="allow", strict=True)


class CombatCounters(ExtensibleResponse):
    """Missing counters are unknown; zero remains a measured total."""

    kills: CombatCount | None = None
    deaths: CombatCount | None = None
    assists: CombatCount | None = None


class RecordingCoverageResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    start: Count
    end: Count
    gaps: list[list[Count]]
    complete: bool

    @model_validator(mode="after")
    def ordered_intervals(self) -> Self:
        if self.start > self.end or any(
            len(gap) != 2 or not self.start <= gap[0] < gap[1] <= self.end for gap in self.gaps
        ):
            raise ValueError("Invalid recording intervals")
        if self.complete and (self.gaps or self.start > 15):
            raise ValueError("Complete coverage cannot have an unknown beginning or gaps")
        return self


class FindingEvidenceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    field: FindingField
    source: str
    precision: Precision
    value: Count
    observed_at: Count | None
    coverage: RecordingCoverageResponse | None

    @model_validator(mode="after")
    def source_matches_field(self) -> Self:
        if validated_evidence(self.model_dump()) is None:
            raise ValueError("Finding source, field, precision or time is inconsistent")
        return self


class FindingResponse(ExtensibleResponse):
    id: Annotated[str, Field(min_length=1)]
    params: dict[str, Any]
    # Old stored/extension findings remain readable; unset evidence stays unset.
    evidence: list[FindingEvidenceResponse] = Field(default_factory=list)
    kind: Literal["strength", "improve"] | None = None
    section: str | None = None
    severity: Count | None = None
    weight: Annotated[StrictFloat, Field(ge=0, allow_inf_nan=False)] | None = None

    @model_validator(mode="after")
    def measurement_matches_finding(self) -> Self:
        permitted = FINDING_FIELDS.get(self.id, ())
        if any(
            row.field not in permitted or row.value != count(self.params.get(PARAMS[row.field]))
            for row in self.evidence
        ):
            raise ValueError("Evidence differs from the finding field or parameters")
        return self


class MatchAnalysis(ExtensibleResponse):
    headline: CombatCounters
    strengths: list[FindingResponse] | None = None
    improvements: list[FindingResponse] | None = None
    evidence_findings: list[FindingResponse] | None = None
    recording_coverage: RecordingCoverageResponse | None = None


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


class CareerStreak(ExtensibleResponse):
    win: bool
    length: Count


class CareerHero(ExtensibleResponse):
    hero: str
    hero_id: Count | None
    matches: Count
    wins: Count
    winrate: Percent | None


class CareerSeriesItem(ExtensibleResponse):
    match_id: StoredMatchId
    hero: str | None
    win: bool | None


class CareerResponse(ExtensibleResponse):
    linked: bool
    matches: Count | None = None
    analyzed: Count | None = None
    wins: Count | None = None
    losses: Count | None = None
    winrate: Percent | None = None
    streak: CareerStreak | None = None
    heroes: list[CareerHero] | None = None
    hero_filter: Count | None = None
    hero_choices: list[MatchHeroCount] | None = None
    series: list[CareerSeriesItem] | None = None


class ProfilePlayer(ExtensibleResponse):
    name: str | None
    avatar_url: str | None
    rank_tier: Count | None
    rank_label: str | None


class ProfileLevel(ExtensibleResponse):
    level: Annotated[Count, Field(ge=1)]
    xp: Count
    into: Count
    need: Annotated[Count, Field(ge=1)]


class ProfileStats(ExtensibleResponse):
    app_games: Count
    app_wins: Count
    app_winrate: Percent | None
    app_hours: Hours
    all_games: Count
    week_games: Count


class ProfileSparks(ExtensibleResponse):
    balance: Count
    earned: Count
    spent: Count


class ProfileRatingPoint(ExtensibleResponse):
    t: StrictInt
    mmr: SignedCount
    win: bool | None = None
    hero_id: Count | None = None
    match_id: StoredMatchId | None = None
    anchor: bool | None = None


class ProfileRating(ExtensibleResponse):
    source: Literal["manual", "medal"]
    # The existing graph extrapolates backwards; estimates can be negative.
    current: SignedCount
    peak: SignedCount
    lowest: SignedCount
    gain_from_lowest: Count
    change_20: SignedCount
    wins_20: Count
    losses_20: Count
    games: Count
    step: Count
    points: list[ProfileRatingPoint]


class ProfileCore(ExtensibleResponse):
    player: ProfilePlayer
    level: ProfileLevel
    rating: ProfileRating | None
    stats: ProfileStats
    sparks: ProfileSparks


class ProfileResponse(ExtensibleResponse):
    profile: ProfileCore | None


def analysis_core_valid(value: object) -> bool:
    """Check cached/imported cores without coercing or replacing stored extensions."""
    try:
        MatchAnalysis.model_validate(value)
    except ValidationError:
        return False
    return True
