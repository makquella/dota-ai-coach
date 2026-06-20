#!/usr/bin/env python3
"""
Compare fallback-only and local LLM blocking simulation reports.

Run from backend/:
    python scripts/compare_simulation_reports.py --latest-two
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BACKEND_DIR = Path(__file__).resolve().parents[1]
RESULTS_DIR = BACKEND_DIR / "simulation_results"
REPORT_PATTERN = "match_advice_simulation_*.json"

METRICS = [
    "source_type",
    "duration_minutes",
    "total_states_processed",
    "states_per_minute",
    "total_advice_shown",
    "advice_per_minute",
    "fits_duration_target",
    "active_advice_count",
    "monitoring_count",
    "pinned_advice_count",
    "repeated_advice_suppressed_count",
    "urgent_advice_count",
    "coaching_advice_count",
    "fallback_count",
    "llm_count",
    "llm_applied_count",
    "llm_applied_rate",
    "llm_skipped_by_policy_count",
    "llm_timeout_count",
    "llm_invalid_count",
    "stale_response_count",
    "average_latency",
    "p95_latency",
    "decision_points",
]

ZERO_DEFAULT_METRICS = {
    "active_advice_count",
    "monitoring_count",
    "pinned_advice_count",
    "repeated_advice_suppressed_count",
    "urgent_advice_count",
    "coaching_advice_count",
    "fallback_count",
    "llm_count",
    "llm_applied_count",
    "llm_applied_rate",
    "llm_skipped_by_policy_count",
    "llm_timeout_count",
    "llm_invalid_count",
    "stale_response_count",
    "average_latency",
    "p95_latency",
}


def main() -> int:
    args = _parse_args()
    try:
        fallback_path, llm_path = _select_reports(args)
        fallback = _load_report(fallback_path)
        llm = _load_report(llm_path)
        rows = _comparison_rows(fallback, llm)
        markdown = _build_markdown(
            fallback=fallback,
            llm=llm,
            fallback_path=fallback_path,
            llm_path=llm_path,
            rows=rows,
        )
        output_md = _resolve_output(args.output_md, "comparison_fallback_vs_llm.md")
        output_md.parent.mkdir(parents=True, exist_ok=True)
        output_md.write_text(markdown, encoding="utf-8")

        output_csv = _resolve_optional_output(args.output_csv)
        if output_csv is not None:
            output_csv.parent.mkdir(parents=True, exist_ok=True)
            _write_csv(output_csv, rows)

    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Markdown comparison saved: {output_md}")
    if output_csv is not None:
        print(f"CSV comparison saved: {output_csv}")
    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare fallback-only and local LLM blocking simulation reports.",
    )
    parser.add_argument(
        "--fallback-report",
        help="Path to a fallback-only match_advice_simulation_*.json report.",
    )
    parser.add_argument(
        "--llm-report",
        help="Path to a local LLM match_advice_simulation_*.json report.",
    )
    parser.add_argument(
        "--latest-two",
        action="store_true",
        help="Use the latest two simulation reports and infer fallback vs LLM mode.",
    )
    parser.add_argument(
        "--output-md",
        help="Markdown output path. Defaults to simulation_results/comparison_fallback_vs_llm.md.",
    )
    parser.add_argument(
        "--output-csv",
        help="Optional CSV output path.",
    )
    return parser.parse_args()


def _select_reports(args: argparse.Namespace) -> tuple[Path, Path]:
    if args.latest_two:
        if args.fallback_report or args.llm_report:
            raise ValueError("Use either --latest-two or explicit report paths, not both.")
        return _latest_two_reports()

    if not args.fallback_report or not args.llm_report:
        raise ValueError("Provide --fallback-report and --llm-report, or use --latest-two.")

    fallback_path = _resolve_input(args.fallback_report)
    llm_path = _resolve_input(args.llm_report)
    _validate_report_exists(fallback_path)
    _validate_report_exists(llm_path)
    return fallback_path, llm_path


def _latest_two_reports() -> tuple[Path, Path]:
    reports = sorted(
        RESULTS_DIR.glob(REPORT_PATTERN),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if len(reports) < 2:
        raise ValueError(f"Need at least two reports in {RESULTS_DIR}.")

    latest = reports[:2]
    classified = [(path, _infer_mode(_load_report(path))) for path in latest]
    fallback = [path for path, mode in classified if mode == "fallback"]
    llm = [path for path, mode in classified if mode == "llm"]
    ambiguous = [path.name for path, mode in classified if mode == "ambiguous"]

    if len(fallback) == 1 and len(llm) == 1:
        return fallback[0], llm[0]

    details = ", ".join(f"{path.name}: {mode}" for path, mode in classified)
    if ambiguous:
        raise ValueError(f"Latest two reports are ambiguous ({details}). Use explicit paths.")
    raise ValueError(f"Latest two reports are not one fallback and one LLM report ({details}). Use explicit paths.")


def _infer_mode(report: dict[str, Any]) -> str:
    if bool(report.get("simulation_llm_blocking")) or _number(report.get("llm_applied_count")) > 0:
        return "llm"
    if _number(report.get("llm_count")) == 0 or report.get("simulation_use_llm") is False:
        return "fallback"
    return "ambiguous"


def _load_report(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"Report not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON report {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"Report is not a JSON object: {path}")
    return data


def _comparison_rows(fallback: dict[str, Any], llm: dict[str, Any]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for metric in METRICS:
        rows.append(
            {
                "metric": metric,
                "fallback": _format_value(fallback.get(metric), metric),
                "llm": _format_value(llm.get(metric), metric),
                "comment": _metric_comment(metric, fallback, llm),
            }
        )
    return rows


def _build_markdown(
    *,
    fallback: dict[str, Any],
    llm: dict[str, Any],
    fallback_path: Path,
    llm_path: Path,
    rows: list[dict[str, str]],
) -> str:
    lines = [
        "# Fallback vs Local LLM Simulation Comparison",
        "",
        "## Scenario",
        "",
        f"- fallback report: `{fallback_path}`",
        f"- local LLM report: `{llm_path}`",
        f"- source_type: `{_scenario_value(fallback, llm, 'source_type')}`",
        f"- duration: `{_scenario_value(fallback, llm, 'duration_minutes')}` minutes",
        f"- states processed: `{_scenario_value(fallback, llm, 'total_states_processed')}`",
    ]
    confidence = fallback.get("context_confidence_distribution") or llm.get("context_confidence_distribution")
    if confidence:
        lines.append(f"- context confidence distribution: `{_format_value(confidence)}`")

    lines.extend(
        [
            "",
            "## Summary Table",
            "",
            "| Metric | Fallback-only | Local LLM blocking | Comment |",
            "|---|---:|---:|---|",
        ]
    )
    for row in rows:
        lines.append(
            f"| {_md_cell(row['metric'])} | {_md_cell(row['fallback'])} | "
            f"{_md_cell(row['llm'])} | {_md_cell(row['comment'])} |"
        )

    lines.extend(
        [
            "",
            "## Decision Point Distribution",
            "",
            "### Fallback-only",
            "",
            _decision_points_table(fallback.get("decision_points", {})),
            "",
            "### Local LLM blocking",
            "",
            _decision_points_table(llm.get("decision_points", {})),
            "",
            "## Interpretation",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in _interpretation(fallback, llm))
    lines.append("")
    lines.append(f"_Generated at {datetime.now(timezone.utc).isoformat()}._")
    lines.append("")
    return "\n".join(lines)


def _decision_points_table(value: Any) -> str:
    if not isinstance(value, dict) or not value:
        return "_No decision point data available._"
    lines = [
        "| Decision point | Count |",
        "|---|---:|",
    ]
    for key, count in sorted(value.items(), key=lambda item: (-_number(item[1]), str(item[0]))):
        lines.append(f"| {_md_cell(key)} | {_format_value(count)} |")
    return "\n".join(lines)


def _interpretation(fallback: dict[str, Any], llm: dict[str, Any]) -> list[str]:
    notes: list[str] = []
    if _number(fallback.get("total_advice_shown")) == _number(llm.get("total_advice_shown")):
        notes.append("Advice frequency was controlled by the local policy and scheduler; the LLM did not increase hint volume.")
    else:
        notes.append("Advice frequency changed between runs; check scheduler settings and decision-point distribution before attributing the difference to wording quality.")

    if _number(llm.get("llm_applied_count")) > 0 and _number(llm.get("stale_response_count")) == 0:
        notes.append("Blocking mode successfully applied LLM responses offline without stale-response losses.")

    if _number(llm.get("average_latency")) > 0:
        notes.append("The local LLM can improve wording at the cost of added per-advice latency.")

    if _number(llm.get("llm_timeout_count")) == 0 and _number(llm.get("llm_invalid_count")) == 0:
        notes.append("The local LLM was stable in this test: no timeouts or invalid responses were reported.")

    if _number(llm.get("llm_skipped_by_policy_count")) > 0:
        notes.append("Some advice remained fallback-first by policy, especially urgent low-HP, death review, or status-safe cases.")

    notes.append("Priority and time_window remain controlled by local advice_policy, even when LLM wording is applied.")
    return notes


def _metric_comment(metric: str, fallback: dict[str, Any], llm: dict[str, Any]) -> str:
    if metric == "total_advice_shown":
        if _number(fallback.get(metric)) == _number(llm.get(metric)):
            return "Same frequency; scheduler controlled volume."
        return "Different volume; inspect decision points."
    if metric == "advice_per_minute":
        return "Useful for overload check."
    if metric == "fits_duration_target":
        return "Pass/fail against expected hints for this replay duration."
    if metric in {"average_latency", "p95_latency"}:
        return "LLM latency cost; fallback should stay near zero."
    if metric == "llm_applied_count":
        return "How many full advice events used LLM wording."
    if metric == "llm_skipped_by_policy_count":
        return "Safety skips for urgent/death/status-like advice."
    if metric in {"llm_timeout_count", "llm_invalid_count", "stale_response_count"}:
        return "Should stay low for stable offline comparison."
    if metric == "fallback_count":
        return "Fallback remains the baseline safety layer."
    if metric == "decision_points":
        return "See distribution below."
    return ""


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["metric", "fallback", "llm", "comment"])
        writer.writeheader()
        writer.writerows(rows)


def _resolve_input(value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    if path.exists():
        return path
    backend_relative = BACKEND_DIR / path
    if backend_relative.exists():
        return backend_relative
    return path


def _resolve_output(value: str | None, default_name: str) -> Path:
    path = Path(value) if value else RESULTS_DIR / default_name
    if path.is_absolute():
        return path
    if path.parent == Path("."):
        return RESULTS_DIR / path
    return path


def _resolve_optional_output(value: str | None) -> Path | None:
    if not value:
        return None
    return _resolve_output(value, "comparison_fallback_vs_llm.csv")


def _validate_report_exists(path: Path) -> None:
    if not path.exists():
        raise ValueError(f"Report not found: {path}")


def _scenario_value(fallback: dict[str, Any], llm: dict[str, Any], key: str) -> str:
    fallback_value = fallback.get(key)
    llm_value = llm.get(key)
    if fallback_value == llm_value:
        return _format_value(fallback_value, key)
    return f"{_format_value(fallback_value, key)} / {_format_value(llm_value, key)}"


def _format_value(value: Any, metric: str | None = None) -> str:
    if value is None:
        if metric in {"average_latency", "p95_latency"}:
            return "0.000s"
        if metric == "llm_applied_rate":
            return "0.0%"
        if metric in ZERO_DEFAULT_METRICS:
            return "0"
        return ""
    if isinstance(value, bool):
        return "yes" if value else "no"
    if metric == "llm_applied_rate" and isinstance(value, (int, float)):
        return f"{value * 100:.1f}%"
    if metric in {"average_latency", "p95_latency"} and isinstance(value, (int, float)):
        return f"{value:.3f}s"
    if isinstance(value, float):
        return f"{value:.2f}".rstrip("0").rstrip(".")
    if isinstance(value, dict):
        return json.dumps(value, sort_keys=True)
    return str(value)


def _number(value: Any) -> float:
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _md_cell(value: Any) -> str:
    return str(value).replace("\n", " ").replace("|", "\\|").strip()


if __name__ == "__main__":
    raise SystemExit(main())
