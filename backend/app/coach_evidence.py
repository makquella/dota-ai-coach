"""Bind combat/farm counters and GPM/XPM to reported player match metrics.

This is a deliberately small evidence boundary, not a semantic verifier for all
AI prose. Other subjects, time slices and metrics need separate evidence.
"""

from __future__ import annotations

import math
import re
from collections.abc import Mapping
from typing import Literal, TypedDict

from app.finding_evidence import validated_evidence

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
    "kills": r"kills?|вбивств\w*|убивств\w*",
    "deaths": r"deaths?|смерт\w*",
    "assists": r"assists?|асист\w*|ассист\w*|допомог\w*",
}
NUMBER = r"[+−-]?\d+(?:[.,   ]\d+)*(?:\s*(?:k|тис\.?))?"
COUNTERS = {
    field: re.compile(
        rf"(?<![\w:.,])(?P<before>{NUMBER})\s+(?:{label})(?!\w)"
        rf"|(?<!\w)(?:{label})\s*[:=—–]?\s*"
        rf"(?:(?:їх\s+)?було\s+|were\s+|was\s+|total\s+)?"
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
    r"|хвилин\w*|\b(?:на|за)\s+ліні\w*|\b(?:перші|останні)\b"
    r"|\b(?:teammate|enemy|opponent|team)\b|союзник\w*|супротивник\w*|противник\w*|суперник\w*|ворог\w*|ворож\w*|команд\w*",
    re.IGNORECASE,
)


def _value(text: str) -> float:
    # Keep the same UK/EN decimal/thousands conventions as the existing checker.
    text = re.sub(r"(?<=\d)[ \u00a0\u202f](?=\d{3}(?!\d))", "", text)
    text = re.sub(r"(?<=\d),(?=\d{3}(?!\d))", "", text)
    text = text.replace(",", ".").replace("−", "-").strip()
    multiple = 1000 if re.search(r"(?:k|тис\.?)$", text, re.IGNORECASE) else 1
    text = re.sub(r"\s*(?:k|тис\.?)$", "", text, flags=re.IGNORECASE)
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


RateMetric = Literal["gpm", "xpm"]
RATE_METRICS: tuple[RateMetric, ...] = ("gpm", "xpm")


class RateEvidence(TypedDict):
    source: Literal["analysis.headline"]
    field: RateMetric
    observed_at: None
    precision: Literal["reported_match_rate"]
    value: int | float


def rate_evidence(headline: Mapping[str, object]) -> dict[RateMetric, RateEvidence]:
    evidence: dict[RateMetric, RateEvidence] = {}
    for field in RATE_METRICS:
        value = headline.get(field)
        if (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and 0 <= value <= 2**53 - 1
            and math.isfinite(value)
        ):
            evidence[field] = {
                "source": "analysis.headline",
                "field": field,
                "observed_at": None,
                "precision": "reported_match_rate",
                "value": value,
            }
    return evidence


RATE_LABELS: dict[RateMetric, str] = {
    "gpm": r"gpm|gold\s+per\s+minute|золот\w*\s+(?:в|за|на)\s+хвилин\w*",
    "xpm": r"xpm|(?:xp|experience)\s+per\s+minute|досвід\w*\s+(?:в|за|на)\s+хвилин\w*",
}
RATE_PATTERNS = {
    field: re.compile(
        rf"(?<![\w:.,])(?P<before>{NUMBER})\s+(?:{label})(?!\w)"
        rf"|(?<!\w)(?:{label})\s*[:=—–]?\s*"
        rf"(?:(?:їх\s+)?було\s+|(?:was|were|of|total)\s+)?"
        rf"(?P<after>{NUMBER})(?![\w:]|[.,]\d)",
        re.IGNORECASE,
    )
    for field, label in RATE_LABELS.items()
}
RATE_NOUNS = re.compile(r"(?<!\w)(?:" + "|".join(RATE_LABELS.values()) + r")(?!\w)", re.IGNORECASE)


class MatchRateBindings:
    def __init__(self, facts: Mapping[str, object]) -> None:
        rates = facts.get("match_rates")
        self.enabled = isinstance(rates, dict) or any(field in facts for field in RATE_METRICS)
        self.evidence = rate_evidence(rates if isinstance(rates, dict) else facts)
        self.hero = facts.get("hero")

    def problems(self, text: str, *, other_heroes: list[str]) -> list[str]:
        if not self.enabled:
            return []
        claims: list[tuple[RateMetric, float]] = []
        for field, pattern in RATE_PATTERNS.items():
            claims.extend(
                (field, _value(match.group("before") or match.group("after")))
                for match in pattern.finditer(text)
            )
        if not claims:
            return []
        # "Gold per minute" names a metric, not a separate time slice. Any
        # remaining named scope still needs its own evidence.
        scope_text = RATE_NOUNS.sub(" ", text)
        if SCOPED.search(scope_text) or any(
            re.search(r"(?<!\w)" + re.escape(hero) + r"(?!\w)", text, re.IGNORECASE)
            for hero in other_heroes
            if hero != self.hero
        ):
            return ["GPM/XPM requires player match-rate evidence"]
        return [
            f"{field}={value:g} (player match rate: "
            + (str(self.evidence[field]["value"]) if field in self.evidence else "unknown")
            + ")"
            for field, value in claims
            if field not in self.evidence or value != self.evidence[field]["value"]
        ]


FarmMetric = Literal["last_hits", "denies"]
FARM_METRICS: tuple[FarmMetric, ...] = ("last_hits", "denies")


class FarmEvidence(TypedDict):
    source: Literal["analysis.headline"]
    field: FarmMetric
    observed_at: None
    precision: Literal["reported_total"]
    value: int


def farm_evidence(headline: Mapping[str, object]) -> dict[FarmMetric, FarmEvidence]:
    evidence: dict[FarmMetric, FarmEvidence] = {}
    for field in FARM_METRICS:
        value = headline.get(field)
        if isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= 2**53 - 1:
            evidence[field] = {
                "source": "analysis.headline",
                "field": field,
                "observed_at": None,
                "precision": "reported_total",
                "value": value,
            }
    return evidence


FARM_LABELS: dict[FarmMetric, str] = {
    "last_hits": r"last[ -]+hits?|lh|добиван\w*|добит\w*\s+кріп\w*",
    "denies": r"denies|deny|dn|дена\w*",
}
FARM_PATTERNS = {
    field: re.compile(
        rf"(?<![\w:.,])(?P<before>{NUMBER})\s+(?:{label})(?!\w)"
        rf"|(?<!\w)(?:{label})\s*[:=—–]?\s*"
        rf"(?:(?:їх\s+)?було\s+|(?:was|were|of|total)\s+)?"
        rf"(?P<after>{NUMBER})(?![\w:]|[.,]\d)",
        re.IGNORECASE,
    )
    for field, label in FARM_LABELS.items()
}
FARM_NOUNS = re.compile(r"(?<!\w)(?:" + "|".join(FARM_LABELS.values()) + r")(?!\w)", re.IGNORECASE)

FarmSubject = Literal["player", "opponent"]


class FarmSliceEvidence(TypedDict):
    source: Literal[
        "analysis.lane.points",
        "analysis.peers.me",
        "analysis.peers.peers[0].metrics",
        "opendota.lh_t",
        "gsi.samples",
    ]
    field: FarmMetric
    subject: FarmSubject
    hero: str | None
    observed_at: Literal[600]
    precision: Literal["reported_sample"]
    value: int


def farm_slice_evidence(lane: Mapping[str, object]) -> list[FarmSliceEvidence]:
    points = lane.get("points")
    if not isinstance(points, list):
        return _peer_farm_slice_evidence(lane)
    at_10 = [
        point
        for point in points
        if isinstance(point, dict) and type(point.get("minute")) is int and point["minute"] == 10
    ]
    if not at_10:
        return _peer_farm_slice_evidence(lane)
    if len(at_10) != 1:
        return []
    point = at_10[0]
    out: list[FarmSliceEvidence] = []
    subjects: tuple[FarmSubject, ...] = ("player", "opponent")
    for subject in subjects:
        prefix = "" if subject == "player" else "enemy_"
        hero = lane.get("hero" if subject == "player" else "enemy")
        values = farm_evidence(
            {"last_hits": point.get(prefix + "lh"), "denies": point.get(prefix + "dn")}
        )
        for field, row in values.items():
            out.append(
                {
                    "source": "analysis.lane.points",
                    "field": field,
                    "subject": subject,
                    "hero": hero if isinstance(hero, str) else None,
                    "observed_at": 600,
                    "precision": "reported_sample",
                    "value": row["value"],
                }
            )
    return out


def _peer_farm_slice_evidence(context: Mapping[str, object]) -> list[FarmSliceEvidence]:
    peers = context.get("peers")
    if not isinstance(peers, dict):
        peers = {}
    me = peers.get("me")
    others = peers.get("peers")
    opponent = (
        others[0] if isinstance(others, list) and others and isinstance(others[0], dict) else {}
    )
    them = opponent.get("metrics")
    out: list[FarmSliceEvidence] = []
    subjects: tuple[FarmSubject, ...] = ("player", "opponent")
    for subject in subjects:
        metrics = me if subject == "player" else them
        value = sample_farm_count(metrics.get("lh_10") if isinstance(metrics, dict) else None)
        if value is None or (subject == "opponent" and opponent.get("enemy") is not True):
            continue
        hero = context.get("hero") if subject == "player" else opponent.get("hero")
        out.append(
            {
                "source": "analysis.peers.me"
                if subject == "player"
                else "analysis.peers.peers[0].metrics",
                "field": "last_hits",
                "subject": subject,
                "hero": hero if isinstance(hero, str) else None,
                "observed_at": 600,
                "precision": "reported_sample",
                "value": value,
            }
        )
    finding = validated_evidence(context.get("finding_lh10"))
    player_hero = context.get("hero")
    if (
        finding
        and finding["field"] == "lh10"
        and finding["precision"] == "sample"
        and not any(row["subject"] == "player" for row in out)
    ):
        out.append(
            {
                "source": "opendota.lh_t"
                if finding["source"] == "opendota.lh_t"
                else "gsi.samples",
                "field": "last_hits",
                "subject": "player",
                "hero": player_hero if isinstance(player_hero, str) else None,
                "observed_at": 600,
                "precision": "reported_sample",
                "value": finding["value"],
            }
        )
    return out


def sample_farm_count(value: object) -> int | None:
    # Peer analysis stores numeric metrics as floats, even integral counts.
    if isinstance(value, float) and math.isfinite(value) and value.is_integer():
        value = int(value)
    row = farm_evidence({"last_hits": value}).get("last_hits")
    return row["value"] if row is not None else None


def farm_slice_facts(context: Mapping[str, object]) -> dict[str, object]:
    """Rebuild the prompt ledger exclusively from validated source measurements."""
    rows = farm_slice_evidence(context)
    hero = context.get("hero")
    enemy = context.get("enemy")
    out: dict[str, object] = {
        "hero": hero if isinstance(hero, str) else None,
        "enemy": enemy if isinstance(enemy, str) else None,
        "points": [],
        "peers": {},
    }
    lane_rows = [row for row in rows if row["source"] == "analysis.lane.points"]
    if lane_rows:
        point: dict[str, int] = {"minute": 10}
        for row in lane_rows:
            prefix = "" if row["subject"] == "player" else "enemy_"
            point[prefix + ("lh" if row["field"] == "last_hits" else "dn")] = row["value"]
        out["points"] = [point]
    else:
        me: dict[str, int] = {}
        peers: list[dict[str, object]] = []
        for row in rows:
            if row["subject"] == "player":
                me["lh_10"] = row["value"]
            else:
                peers.append(
                    {"hero": row["hero"], "enemy": True, "metrics": {"lh_10": row["value"]}}
                )
        out["peers"] = {"me": me, "peers": peers}
    return out


FARM_AT_10 = re.compile(
    r"(?<![\d:])10:00(?![\d:])"
    r"|(?<!\w)(?:at|by)\s+(?:minute\s+10|10(?:th)?\s+minutes?)(?!\w)"
    r"|(?<!\w)(?:до|на)\s+10(?:-?(?:й|ї|у|ту))?\s+хвилин\w*",
    re.IGNORECASE,
)


class MatchFarmBindings:
    def __init__(self, facts: Mapping[str, object]) -> None:
        farm = facts.get("match_farm")
        self.enabled = (
            isinstance(farm, dict)
            or isinstance(facts.get("match_farm_at_10"), dict)
            or any(field in facts for field in FARM_METRICS)
        )
        self.evidence = farm_evidence(farm if isinstance(farm, dict) else facts)
        self.hero = facts.get("hero")
        lane = facts.get("match_farm_at_10")
        self.slice_evidence = farm_slice_evidence(lane if isinstance(lane, dict) else {})

    def problems(self, text: str, *, other_heroes: list[str]) -> list[str]:
        if not self.enabled:
            return []
        claims: list[tuple[FarmMetric, float]] = []
        for field, pattern in FARM_PATTERNS.items():
            claims.extend(
                (field, _value(match.group("before") or match.group("after")))
                for match in pattern.finditer(text)
            )
        if not claims:
            return []
        if FARM_AT_10.search(text):
            return self._slice_problems(text, claims, other_heroes)
        # "Last hits" names the metric; "last 10 minutes" still needs a slice.
        scope_text = FARM_NOUNS.sub(" ", text)
        if SCOPED.search(scope_text) or any(
            re.search(r"(?<!\w)" + re.escape(hero) + r"(?!\w)", text, re.IGNORECASE)
            for hero in other_heroes
            if hero != self.hero
        ):
            return ["farm counter requires player match-total evidence"]
        return [
            f"{field}={value:g} (player farm total: "
            + (str(self.evidence[field]["value"]) if field in self.evidence else "unknown")
            + ")"
            for field, value in claims
            if field not in self.evidence or value != self.evidence[field]["value"]
        ]

    def _slice_problems(
        self, text: str, claims: list[tuple[FarmMetric, float]], other_heroes: list[str]
    ) -> list[str]:
        player = {
            row["field"]: row["value"] for row in self.slice_evidence if row["subject"] == "player"
        }
        enemy = {
            row["field"]: row["value"]
            for row in self.slice_evidence
            if row["subject"] == "opponent"
        }
        enemy_hero = next(
            (row["hero"] for row in self.slice_evidence if row["subject"] == "opponent"), None
        )
        scope_text = text
        comparisons: list[tuple[FarmMetric, float]] = []
        if enemy_hero:
            for field, label in FARM_LABELS.items():
                pattern = re.compile(
                    rf"(?<![\w:.,]){NUMBER}\s+(?:{label})"
                    rf"(?:\s+(?:до|на|at|by)\s+10:00)?\s+(?:проти|against|versus|vs\.?)\s+"
                    rf"(?P<count>{NUMBER})\s+(?:(?:у|в|for|on)\s+)?{re.escape(enemy_hero)}(?!\w)",
                    re.IGNORECASE,
                )
                comparisons.extend(
                    (field, _value(m.group("count"))) for m in pattern.finditer(text)
                )
                scope_text = pattern.sub(" ", scope_text)
        scope_text = FARM_AT_10.sub(" ", FARM_NOUNS.sub(" ", scope_text))
        if SCOPED.search(scope_text) or any(
            re.search(r"(?<!\w)" + re.escape(hero) + r"(?!\w)", scope_text, re.IGNORECASE)
            for hero in other_heroes
            if hero != self.hero
        ):
            return ["farm counter requires subject/time-slice evidence"]
        return [
            f"{field}={value:g} (player farm at 10:00: "
            + (str(player[field]) if field in player else "unknown")
            + ")"
            for field, value in claims
            if field not in player or value != player[field]
        ] + [
            f"enemy {field}={value:g} (enemy farm at 10:00: "
            + (str(enemy[field]) if field in enemy else "unknown")
            + ")"
            for field, value in comparisons
            if field not in enemy or value != enemy[field]
        ]
