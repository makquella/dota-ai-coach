"""
Replay GSI-like states into the local backend for desktop overlay demos.

This is an offline demo helper. It does not launch Dota 2, parse replays,
read memory, read the screen, or automate input. It feeds existing
GSI-like simulation states into the backend demo endpoint, which uses the
same decision/scheduler/recommender path as the overlay.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any


BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.coach_summary import summary_to_markdown  # noqa: E402
from app.deep_replay_review import (  # noqa: E402
    build_deep_replay_review,
    deep_replay_review_to_markdown,
)

DEFAULT_SIMULATION_FILE = (
    REPO_ROOT
    / "data/match_simulations/replay_gsi_like_match_8843382732_pl_20_30.jsonl"
)


def main() -> int:
    args = _parse_args()
    simulation_file = Path(args.simulation_file)
    if not simulation_file.exists():
        print(f"Simulation file not found: {simulation_file}", file=sys.stderr, flush=True)
        return 1

    backend_url = str(args.backend_url).rstrip("/")
    entries = _load_entries(
        simulation_file,
        start_time=args.start_time,
        end_time=args.end_time,
        max_states=args.max_states,
    )
    if not entries:
        print("No states selected for demo playback.", file=sys.stderr, flush=True)
        return 1

    if args.reset_session:
        _post_json(f"{backend_url}/session/reset", {})

    print(f"Demo playback: {simulation_file}", flush=True)
    print(f"Backend: {backend_url}", flush=True)
    print(
        f"States: {len(entries)} | speed: {args.speed}x | advice hold: {args.advice_hold_seconds}s",
        flush=True,
    )
    print("Press Ctrl+C to stop.\n", flush=True)

    previous_timestamp: int | None = None
    previous_print_bucket: int | None = None
    processed = 0
    advice_shown = 0
    advice_gaps: list[float] = []

    try:
        for entry in entries:
            timestamp_seconds = int(entry.get("timestamp_seconds", 0))
            state = entry.get("state")
            if not isinstance(state, dict):
                continue

            overlay = _send_demo_state(
                backend_url=backend_url,
                timestamp_seconds=timestamp_seconds,
                state=state,
                simulation_file=simulation_file,
                speed=args.speed,
            )
            processed += 1

            is_new_advice = bool(overlay.get("new_advice") and overlay.get("recommendation"))
            if is_new_advice:
                advice_shown += 1
                gap = overlay.get("game_time_gap_since_previous_advice")
                if isinstance(gap, (int, float)):
                    advice_gaps.append(float(gap))

            print_bucket = timestamp_seconds // max(1, args.print_every_seconds)
            should_print = is_new_advice
            if args.verbose and not args.only_advice_events and print_bucket != previous_print_bucket:
                should_print = True
            if should_print:
                previous_print_bucket = print_bucket
                if is_new_advice and not args.verbose:
                    print(_format_advice_line(timestamp_seconds, overlay), flush=True)
                else:
                    print(_format_status_line(timestamp_seconds, state, overlay), flush=True)

            if is_new_advice and args.advice_hold_seconds > 0:
                time.sleep(args.advice_hold_seconds)
            elif not args.only_advice_events:
                delay = _playback_delay(previous_timestamp, timestamp_seconds, args.speed)
                if delay > 0:
                    time.sleep(delay)

            previous_timestamp = timestamp_seconds
    except KeyboardInterrupt:
        print("\nDemo playback stopped.", flush=True)
        return 130

    print(
        f"\nDemo playback complete. States sent: {processed}. Advice shown: {advice_shown}.",
        flush=True,
    )
    if advice_gaps:
        compact_gaps = ", ".join(str(round(gap, 1)) for gap in advice_gaps)
        print(f"Game-time gaps between shown advice: {compact_gaps}", flush=True)
        short_gaps = [gap for gap in advice_gaps if gap < 30]
        if short_gaps:
            compact_short_gaps = ", ".join(str(round(gap, 1)) for gap in short_gaps)
            print(
                "Short gaps below 30s: "
                f"{compact_short_gaps} (allowed for urgent/safety interrupts such as LOW_HP).",
                flush=True,
            )
        else:
            print("No shown-advice game-time gap below 30 seconds.", flush=True)
    _export_reviews_if_requested(args, backend_url, entries)
    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Replay GSI-like states into the overlay backend.")
    parser.add_argument(
        "--simulation-file",
        default=str(DEFAULT_SIMULATION_FILE),
        help="Path to replay_gsi_like JSONL file.",
    )
    parser.add_argument(
        "--backend-url",
        default="http://127.0.0.1:8000",
        help="Local backend base URL.",
    )
    parser.add_argument(
        "--speed",
        type=float,
        default=20.0,
        help="Playback speed multiplier for non-advice states.",
    )
    parser.add_argument("--start-time", type=int, default=None, help="First timestamp_seconds to send.")
    parser.add_argument("--end-time", type=int, default=None, help="Last timestamp_seconds to send.")
    parser.add_argument("--max-states", type=int, default=None, help="Maximum number of states to send.")
    parser.add_argument(
        "--only-advice-events",
        action="store_true",
        help="Fast-forward non-advice states while still feeding them to the backend.",
    )
    parser.add_argument(
        "--advice-hold-seconds",
        type=float,
        default=3.0,
        help="Real seconds to keep each new advice card visible during demo playback.",
    )
    parser.add_argument(
        "--print-every-seconds",
        type=int,
        default=30,
        help="With --verbose, print one non-advice status line per simulated interval.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print every periodic cooldown/monitoring status line for debugging.",
    )
    parser.add_argument(
        "--no-reset-session",
        dest="reset_session",
        action="store_false",
        help="Do not reset backend match memory/scheduler before playback.",
    )
    parser.add_argument(
        "--export-summary",
        default=None,
        help="Optional Markdown path for coach session summary.",
    )
    parser.add_argument(
        "--export-summary-json",
        default=None,
        help="Optional JSON path for coach session summary.",
    )
    parser.add_argument(
        "--export-deep-review",
        default=None,
        help="Optional Markdown path for Deep Replay Review v0.",
    )
    parser.add_argument(
        "--export-deep-review-json",
        default=None,
        help="Optional JSON path for Deep Replay Review v0.",
    )
    parser.set_defaults(reset_session=True)
    args = parser.parse_args()
    if args.speed <= 0:
        parser.error("--speed must be greater than 0")
    return args


def _load_entries(
    path: Path,
    *,
    start_time: int | None,
    end_time: int | None,
    max_states: int | None,
) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            entry = json.loads(line)
            timestamp_seconds = int(entry.get("timestamp_seconds", 0))
            if start_time is not None and timestamp_seconds < start_time:
                continue
            if end_time is not None and timestamp_seconds > end_time:
                continue
            entries.append(entry)
            if max_states is not None and len(entries) >= max_states:
                break
    return entries


def _send_demo_state(
    *,
    backend_url: str,
    timestamp_seconds: int,
    state: dict[str, Any],
    simulation_file: Path,
    speed: float,
) -> dict[str, Any]:
    payload = {
        "timestamp_seconds": timestamp_seconds,
        "simulation_file": str(simulation_file),
        "speed": speed,
        "state": state,
    }
    response = _post_json(f"{backend_url}/demo/replay-state", payload)
    overlay = response.get("overlay")
    return overlay if isinstance(overlay, dict) else {}


def _post_json(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"Backend error {exc.code} from {url}: {body}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"Could not reach backend at {url}: {exc}") from exc


def _get_json(url: str) -> dict[str, Any]:
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"Backend error {exc.code} from {url}: {body}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"Could not reach backend at {url}: {exc}") from exc


def _export_reviews_if_requested(
    args: argparse.Namespace,
    backend_url: str,
    entries: list[dict[str, Any]],
) -> None:
    wants_simple_summary = bool(args.export_summary or args.export_summary_json)
    wants_deep_review = bool(args.export_deep_review or args.export_deep_review_json)
    if not wants_simple_summary and not wants_deep_review:
        return

    summary = _get_json(f"{backend_url}/demo/session-summary")
    if args.export_summary:
        markdown_path = _resolve_export_path(args.export_summary)
        markdown_path.parent.mkdir(parents=True, exist_ok=True)
        markdown_path.write_text(summary_to_markdown(summary), encoding="utf-8")
        print(f"Coach summary saved: {markdown_path}")

    if args.export_summary_json:
        json_path = _resolve_export_path(args.export_summary_json)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(
            json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"Coach summary JSON saved: {json_path}")

    if wants_deep_review:
        overview = summary.get("session_overview") if isinstance(summary.get("session_overview"), dict) else {}
        deep_review = build_deep_replay_review(
            processed_entries=entries,
            advice_history=summary.get("advice_history") if isinstance(summary.get("advice_history"), list) else [],
            scheduler_stats=overview.get("suppression_metrics") if isinstance(overview.get("suppression_metrics"), dict) else {},
        )

        if args.export_deep_review:
            deep_markdown_path = _resolve_export_path(args.export_deep_review)
            deep_markdown_path.parent.mkdir(parents=True, exist_ok=True)
            deep_markdown_path.write_text(
                deep_replay_review_to_markdown(deep_review),
                encoding="utf-8",
            )
            print(f"Deep replay review saved: {deep_markdown_path}")

        if args.export_deep_review_json:
            deep_json_path = _resolve_export_path(args.export_deep_review_json)
            deep_json_path.parent.mkdir(parents=True, exist_ok=True)
            deep_json_path.write_text(
                json.dumps(deep_review, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            print(f"Deep replay review JSON saved: {deep_json_path}")


def _resolve_export_path(path_value: str) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = Path(path_value.replace("<timestamp>", timestamp))
    return path if path.is_absolute() else Path.cwd() / path


def _playback_delay(previous_timestamp: int | None, timestamp_seconds: int, speed: float) -> float:
    if previous_timestamp is None:
        return 0.0
    delta = max(0, timestamp_seconds - previous_timestamp)
    return delta / speed


def _format_status_line(timestamp_seconds: int, state: dict[str, Any], overlay: dict[str, Any]) -> str:
    recommendation = overlay.get("recommendation")
    action = ""
    if isinstance(recommendation, dict):
        action = str(recommendation.get("action") or "")
    hero = str(state.get("hero") or overlay.get("hero") or "Unknown")
    hp = state.get("hp_percent", overlay.get("hp_percent", "?"))
    stage = overlay.get("stage") or _stage_from_minute(int(state.get("minute", 0)))
    source = overlay.get("source") or "none"
    confidence = overlay.get("context_confidence") or ""
    status = overlay.get("status") or "unknown"
    decision = overlay.get("decision_point") or "NO_ADVICE"
    prefix = f"[{_format_time(timestamp_seconds)}] {hero} HP {hp}% {stage}"
    suffix = f"{status}/{decision} source={source}"
    if confidence:
        suffix += f" confidence={confidence}"
    if overlay.get("suppressed_by_game_time_spacing"):
        suffix += " spacing=suppressed"
    if action:
        suffix += f" | {action}"
    return f"{prefix} -> {suffix}"


def _format_advice_line(timestamp_seconds: int, overlay: dict[str, Any]) -> str:
    recommendation = overlay.get("recommendation")
    action = ""
    if isinstance(recommendation, dict):
        action = str(recommendation.get("action") or "")
    status = overlay.get("status") or "advice"
    decision = overlay.get("decision_point") or "NO_ADVICE"
    gap = overlay.get("game_time_gap_since_previous_advice")
    gap_text = ""
    if isinstance(gap, (int, float)):
        gap_text = f" gap={round(float(gap), 1)}s"
    return f"[{_format_time(timestamp_seconds)}] {status}/{decision}{gap_text} | {action}"


def _format_time(timestamp_seconds: int) -> str:
    timestamp_seconds = max(0, timestamp_seconds)
    return f"{timestamp_seconds // 60:02d}:{timestamp_seconds % 60:02d}"


def _stage_from_minute(minute: int) -> str:
    if minute < 10:
        return "laning"
    if minute < 20:
        return "post-laning"
    return "macro"


if __name__ == "__main__":
    raise SystemExit(main())
