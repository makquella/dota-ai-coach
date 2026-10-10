"""Bind retrospective ward and early-death claims to source findings."""

from __future__ import annotations

import re
from collections.abc import Mapping

from app.coach_evidence import COUNTERS, NUMBER, _value
from app.finding_evidence import FindingEvidence, FindingField, validated_evidence

WARD_LABELS: dict[FindingField, str] = {
    "obs_placed": r"observer\s+wards?|observers?|обсервер(?:-?вард)?\w*|спостережн\w*\s+вард\w*",
    "sen_placed": r"sentry\s+wards?|sentries|сентрі(?:-?вард)?\w*",
}
WARD_PATTERNS = {
    field: re.compile(
        rf"(?<![\w:.,])(?P<before>{NUMBER})\s+(?:{label})(?!\w)"
        rf"|(?<!\w)(?:{label})\s*[:=—–]?\s*(?P<after>{NUMBER})(?![\w:]|[.,]\d)",
        re.IGNORECASE,
    )
    for field, label in WARD_LABELS.items()
}
GENERIC_WARDS = re.compile(rf"(?<![\w:.,]){NUMBER}\s+(?:wards?|вард\w*)(?!\w)", re.IGNORECASE)
ESTIMATE = re.compile(
    r"\b(?:estimated?|approximately|approx|inventory)\b|оцін\w*|приблизно|інвентар\w*",
    re.IGNORECASE,
)
RECORDED = re.compile(
    r"\b(?:recorded|logged|observed)\b|зафіксован\w*|запис\w*|зареєстрован\w*", re.IGNORECASE
)
EARLY = re.compile(
    r"\b(?:before|by)\s+(?:minute\s+10|10(?:th)?\s+minutes?|10:00)(?![\w:])"
    r"|\bfirst\s+10\s+minutes?\b"
    r"|(?<!\w)(?:до|на)\s+10(?:-?(?:й|ї|у|ту))?\s+(?:хвилин\w*)(?!\w)"
    r"|(?<!\w)до\s+10:00(?![\d:])|перші\s+10\s+хвилин\w*",
    re.IGNORECASE,
)
OTHER_SCOPE = re.compile(
    r"\d{1,2}:\d{2}|\b(?:minutes?|per|first|last|teammate|enemy|opponent|team)\b"
    r"|хвилин\w*|союзник\w*|супротивник\w*|противник\w*|суперник\w*|ворог\w*|ворож\w*|команд\w*",
    re.IGNORECASE,
)


class FindingBindings:
    def __init__(self, facts: Mapping[str, object]) -> None:
        self.enabled = "finding_evidence" in facts
        self.hero = facts.get("hero")
        self.evidence: list[FindingEvidence] = []
        groups = facts.get("finding_evidence")
        if isinstance(groups, dict):
            for values in groups.values():
                if isinstance(values, list):
                    self.evidence.extend(
                        row for value in values if (row := validated_evidence(value)) is not None
                    )

    def _measurement(self, field: FindingField) -> FindingEvidence | None:
        rows = [row for row in self.evidence if row["field"] == field]
        if not rows or any(row != rows[0] for row in rows[1:]):
            return None
        return rows[0]

    def _other_subject(self, text: str, heroes: list[str]) -> bool:
        return any(
            re.search(r"(?<!\w)" + re.escape(hero) + r"(?!\w)", text, re.IGNORECASE)
            for hero in heroes
            if hero != self.hero
        )

    def problems(self, text: str, *, other_heroes: list[str]) -> list[str]:
        if not self.enabled:
            return []
        problems = []
        ward_claims = [
            (field, _value(m.group("before") or m.group("after")))
            for field, pattern in WARD_PATTERNS.items()
            for m in pattern.finditer(text)
        ]
        if GENERIC_WARDS.search(text):
            problems.append("ward count requires observer/sentry evidence")
        for field, value in ward_claims:
            row = self._measurement(field)
            if row is None or row["value"] != value:
                problems.append(f"{field}={value:g} (finding measurement: unknown or different)")
            elif row["precision"] == "inventory_estimate" and (
                not ESTIMATE.search(text)
                or row["coverage"] is None
                or not row["coverage"]["complete"]
            ):
                problems.append(
                    "ward count requires a labeled inventory estimate with complete recording"
                )
        if ward_claims and (OTHER_SCOPE.search(text) or self._other_subject(text, other_heroes)):
            problems.append("ward count requires player match scope")
        deaths = list(COUNTERS["deaths"].finditer(text))
        if deaths and EARLY.search(text):
            row = self._measurement("lane_deaths")
            if row is None or any(
                _value(m.group("before") or m.group("after")) != row["value"] for m in deaths
            ):
                problems.append("early deaths differ from recorded finding events")
            if not RECORDED.search(text):
                problems.append("early deaths must be labeled recorded events")
            if OTHER_SCOPE.search(EARLY.sub(" ", text)) or self._other_subject(text, other_heroes):
                problems.append("early deaths require player first-ten-minute scope")
        return problems

    def combat_text(self, text: str, *, other_heroes: list[str]) -> str:
        # Remove only separately verified early-death claims. Other combat
        # assertions in the sentence still pass through the match-total checker.
        if (
            self.enabled
            and EARLY.search(text)
            and not self.problems(text, other_heroes=other_heroes)
        ):
            return COUNTERS["deaths"].sub(" ", text)
        return text
