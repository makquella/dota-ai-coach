"""Validated core of the match-detail wire response; extensions stay intact."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt

CombatCount = Annotated[StrictInt, Field(ge=0, le=2**53 - 1)]
StoredMatchId = Annotated[StrictInt, Field(ge=0, le=2**63 - 1)]


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
