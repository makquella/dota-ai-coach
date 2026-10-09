"""Source measurements for vision, last hits at 10:00 and early-death findings."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any, Literal, TypedDict, cast

FindingField = Literal["obs_placed", "sen_placed", "lh10", "lane_deaths"]
Precision = Literal["reported_total", "log_count", "inventory_estimate", "sample", "carried_sample"]


class RecordingCoverage(TypedDict):
    start: int
    end: int
    gaps: list[list[int]]
    complete: bool


class FindingEvidence(TypedDict):
    field: FindingField
    source: str
    precision: Precision
    value: int
    observed_at: int | None
    coverage: RecordingCoverage | None


def count(value: object) -> int | None:
    return value if type(value) is int and 0 <= value <= 2**53 - 1 else None


def _row(
    field: FindingField,
    source: str,
    precision: Precision,
    value: object,
    observed_at: int | None = None,
    coverage: RecordingCoverage | None = None,
) -> FindingEvidence | None:
    number = count(value)
    if number is None:
        return None
    return {
        "field": field,
        "source": source,
        "precision": precision,
        "value": number,
        "observed_at": observed_at,
        "coverage": deepcopy(coverage),
    }


def recording_coverage(timeline: Mapping[str, Any]) -> RecordingCoverage | None:
    times = sorted(
        {
            s["t"]
            for s in timeline.get("samples") or []
            if isinstance(s, dict) and count(s.get("t")) is not None
        }
    )
    if not times:
        return None
    gaps = [[a, b] for a, b in zip(times, times[1:], strict=False) if b - a > 30]
    duration = count(timeline.get("duration"))
    return {
        "start": times[0],
        "end": times[-1],
        "gaps": gaps,
        "complete": duration is not None
        and times[0] <= 15
        and times[-1] >= duration - 15
        and not gaps,
    }


def opendota_provenance(
    player: Mapping[str, Any],
    *,
    parsed: bool,
    deaths: list[dict[str, Any]],
    death_logs_available: bool,
) -> dict[FindingField, FindingEvidence | None]:
    rows: dict[FindingField, FindingEvidence | None] = {}
    for field, log in [("obs_placed", "obs_log"), ("sen_placed", "sen_log")]:
        field_name: FindingField = "obs_placed" if field == "obs_placed" else "sen_placed"
        events = player.get(log)
        if (
            parsed
            and isinstance(events, list)
            and all(isinstance(e, dict) and type(e.get("time")) is int for e in events)
        ):
            rows[field_name] = _row(field_name, f"opendota.{log}", "log_count", len(events))
        else:
            rows[field_name] = _row(
                field_name, f"opendota.{field}", "reported_total", player.get(field)
            )
    series = player.get("lh_t")
    rows["lh10"] = (
        _row("lh10", "opendota.lh_t", "sample", series[10], 600)
        if isinstance(series, list) and len(series) > 10
        else None
    )
    early = [d for d in deaths if count(d.get("t")) is not None and d["t"] <= 600]
    rows["lane_deaths"] = (
        _row("lane_deaths", "opendota.kills_log", "log_count", len(early))
        if parsed and death_logs_available
        else None
    )
    return rows


def timeline_provenance(timeline: Mapping[str, Any]) -> dict[FindingField, FindingEvidence | None]:
    coverage = recording_coverage(timeline)
    samples = [
        s
        for s in timeline.get("samples") or []
        if isinstance(s, dict)
        and count(s.get("t")) is not None
        and 570 <= s["t"] <= 600
        and count(s.get("lh")) is not None
    ]
    latest = max(samples, key=lambda s: s["t"], default=None)
    early = [
        d
        for d in timeline.get("deaths") or []
        if isinstance(d, dict) and count(d.get("t")) is not None and d["t"] <= 600
    ]
    return {
        "obs_placed": _row(
            "obs_placed",
            "gsi.inventory_changes",
            "inventory_estimate",
            timeline.get("obs_placed"),
            coverage=coverage,
        ),
        "sen_placed": None,
        "lh10": _row(
            "lh10",
            "gsi.samples",
            "sample" if latest["t"] == 600 else "carried_sample",
            latest["lh"],
            latest["t"],
            coverage,
        )
        if latest
        else None,
        "lane_deaths": _row("lane_deaths", "gsi.deaths", "log_count", len(early), coverage=coverage)
        if isinstance(timeline.get("deaths"), list)
        else None,
    }


FINDING_FIELDS: dict[str, tuple[FindingField, ...]] = {
    "wards_low": ("obs_placed",),
    "wards_high": ("obs_placed", "sen_placed"),
    "lh10_low": ("lh10",),
    "lh10_great": ("lh10",),
    "lane_deaths": ("lane_deaths",),
}
PARAMS = {"obs_placed": "obs", "sen_placed": "sen", "lh10": "lh10", "lane_deaths": "count"}

SOURCES: dict[FindingField, dict[str, tuple[Precision, ...]]] = {
    "obs_placed": {
        "opendota.obs_log": ("log_count",),
        "opendota.obs_placed": ("reported_total",),
        "gsi.inventory_changes": ("inventory_estimate",),
    },
    "sen_placed": {"opendota.sen_log": ("log_count",), "opendota.sen_placed": ("reported_total",)},
    "lh10": {"opendota.lh_t": ("sample",), "gsi.samples": ("sample", "carried_sample")},
    "lane_deaths": {"opendota.kills_log": ("log_count",), "gsi.deaths": ("log_count",)},
}


def validated_evidence(value: object) -> FindingEvidence | None:
    if not isinstance(value, dict):
        return None
    field = value.get("field")
    if not isinstance(field, str) or field not in SOURCES or count(value.get("value")) is None:
        return None
    source, precision = value.get("source"), value.get("precision")
    if not isinstance(source, str) or precision not in SOURCES[field].get(source, ()):
        return None
    precision = cast(Precision, precision)
    observed = count(value.get("observed_at"))
    if value.get("observed_at") is not None and observed is None:
        return None
    if field == "lh10":
        if precision == "sample" and (observed is None or observed != 600):
            return None
        if precision == "carried_sample" and (observed is None or not 570 <= observed < 600):
            return None
    elif observed is not None:
        return None
    raw_coverage = value.get("coverage")
    coverage: RecordingCoverage | None = None
    if raw_coverage is not None:
        if not isinstance(raw_coverage, dict) or type(raw_coverage.get("complete")) is not bool:
            return None
        start, end = count(raw_coverage.get("start")), count(raw_coverage.get("end"))
        if start is None or end is None or start > end:
            return None
        gaps = raw_coverage.get("gaps")
        if not isinstance(gaps, list) or any(
            not isinstance(g, list)
            or len(g) != 2
            or any(count(t) is None for t in g)
            or not start <= g[0] < g[1] <= end
            for g in gaps
        ):
            return None
        if raw_coverage["complete"] and (gaps or start > 15):
            return None
        coverage = {
            "start": start,
            "end": end,
            "gaps": deepcopy(gaps),
            "complete": raw_coverage["complete"],
        }
    if source.startswith("gsi.") and coverage is None:
        return None
    if source.startswith("opendota.") and coverage is not None:
        return None
    return _row(field, source, precision, value["value"], observed, coverage)


def analysis_evidence(analysis: Mapping[str, Any]) -> dict[str, list[FindingEvidence]]:
    result: dict[str, list[FindingEvidence]] = {}
    duplicates: set[str] = set()
    findings = analysis.get("evidence_findings")
    if not isinstance(findings, list):
        findings = [*(analysis.get("improvements") or []), *(analysis.get("strengths") or [])]
    for finding in findings:
        if not isinstance(finding, dict):
            continue
        identifier = finding.get("id")
        if not isinstance(identifier, str) or identifier not in FINDING_FIELDS:
            continue
        if identifier in result:
            duplicates.add(identifier)
        fields = FINDING_FIELDS[identifier]
        params = finding.get("params")
        values = finding.get("evidence")
        result[identifier] = (
            [
                row
                for value in values
                if (row := validated_evidence(value)) is not None
                and row["field"] in fields
                and isinstance(params, dict)
                and row["value"] == count(params.get(PARAMS[row["field"]]))
            ]
            if isinstance(values, list)
            else []
        )
    return {key: rows for key, rows in result.items() if key not in duplicates}


def attach_finding_evidence(findings: list[dict[str, Any]], facts: Mapping[str, Any]) -> None:
    provenance = facts.get("provenance") or {}
    for finding in findings:
        rows = [provenance.get(field) for field in FINDING_FIELDS.get(finding["id"], ())]
        finding["evidence"] = [
            row
            for value in rows
            if (row := validated_evidence(value)) is not None
            and row["value"] == count(finding["params"].get(PARAMS[row["field"]]))
        ]
