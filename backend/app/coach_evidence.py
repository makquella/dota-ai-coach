"""Bind quantified combat counters to the player's reported match totals.

This is a deliberately small evidence boundary, not a semantic verifier for all
AI prose. Other subjects, time slices and rates need separate evidence.
"""

from __future__ import annotations

import math
import re
from collections.abc import Mapping
from typing import Literal, TypedDict

CombatMetric = Literal["kills", "deaths", "assists"]
METRICS: tuple[CombatMetric, ...] = ("kills", "deaths", "assists")


class CounterEvidence(TypedDict):
    source: Literal["analysis.headline"]
    field: CombatMetric
    observed_at: None
    precision: Literal["reported_total"]
    value: int


def counter_evidence(headline: Mapping[str, object]) -> dict[CombatMetric, CounterEvidence]:
    evidence: dict[CombatMetric, CounterEvidence] = {}
    for field in METRICS:
        value = headline.get(field)
        if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
            evidence[field] = {
                "source": "analysis.headline",
                "field": field,
                "observed_at": None,
                "precision": "reported_total",
                "value": value,
            }
    return evidence


LABELS: dict[CombatMetric, str] = {
    "kills": r"kills?|убийств\w*",
    "deaths": r"deaths?|смерт\w*",
    "assists": r"assists?|ассист\w*|содействи\w*",
}
NUMBER = r"[+−-]?\d+(?:[.,\u00a0\u202f ]\d+)*(?:\s*(?:k|тыс\.?))?"
COUNTERS = {
    field: re.compile(
        rf"(?<![\w:.,])(?P<before>{NUMBER})\s+(?:{label})(?!\w)"
        rf"|(?<!\w)(?:{label})\s*[:=—–]?\s*"
        rf"(?:(?:их\s+)?было\s+|were\s+|was\s+|total\s+)?"
        rf"(?P<after>{NUMBER})(?![\w:]|[.,]\d)",
        re.IGNORECASE,
    )
    for field, label in LABELS.items()
}
KDA = re.compile(
    r"(?<![\w/.,])(?P<kills>[+−-]?\d+)\s*/\s*(?P<deaths>[+−-]?\d+)"
    r"\s*/\s*(?P<assists>[+−-]?\d+)(?![\w/]|[.,]\d)"
)
SCOPED = re.compile(
    r"\d{1,2}:\d{2}|\b(?:minutes?|per|lane|laning|first|last)\b"
    r"|минут\w*|\b(?:на|за)\s+лини\w*|\b(?:первые|последние)\b"
    r"|\b(?:teammate|enemy|opponent|team)\b|союзник\w*|противник\w*|враг\w*|команд\w*",
    re.IGNORECASE,
)


def _value(text: str) -> float:
    # Keep the same RU/EN decimal/thousands conventions as the existing checker.
    text = re.sub(r"(?<=\d)[ \u00a0\u202f](?=\d{3}(?!\d))", "", text)
    text = re.sub(r"(?<=\d),(?=\d{3}(?!\d))", "", text)
    text = text.replace(",", ".").replace("−", "-").strip()
    multiple = 1000 if re.search(r"(?:k|тыс\.?)$", text, re.IGNORECASE) else 1
    text = re.sub(r"\s*(?:k|тыс\.?)$", "", text, flags=re.IGNORECASE)
    try:
        return float(text) * multiple
    except ValueError:
        return math.nan


class CombatCounterBindings:
    def __init__(self, facts: Mapping[str, object]) -> None:
        totals = facts.get("match_totals")
        # Root fields also support direct developer/checker callers. Nested
        # scoreboard, lane or finding values never license the player's total.
        self.enabled = isinstance(totals, dict) or any(field in facts for field in METRICS)
        self.evidence = counter_evidence(totals if isinstance(totals, dict) else facts)
        self.hero = facts.get("hero")

    def problems(self, text: str, *, other_heroes: list[str]) -> list[str]:
        if not self.enabled:
            return []
        claims: list[tuple[CombatMetric, float]] = []
        for field, pattern in COUNTERS.items():
            claims.extend(
                (field, _value(match.group("before") or match.group("after")))
                for match in pattern.finditer(text)
            )
        for match in KDA.finditer(text):
            claims.extend((field, _value(match.group(field))) for field in METRICS)
        if not claims:
            return []
        # An exact match of the total cannot prove a lane count, a time slice,
        # a rate or somebody else's score. Refuse these ambiguous scopes.
        if SCOPED.search(text) or any(
            re.search(r"(?<!\w)" + re.escape(hero) + r"(?!\w)", text, re.IGNORECASE)
            for hero in other_heroes
            if hero != self.hero
        ):
            return ["combat counter requires subject/time-slice evidence"]
        return [
            f"{field}={value:g} (player match total: "
            + (str(self.evidence[field]["value"]) if field in self.evidence else "unknown")
            + ")"
            for field, value in claims
            if field not in self.evidence or value != self.evidence[field]["value"]
        ]
