"""
Reproducible evaluation of the whole system (numbers for docs/EVALUATION.md).

Run from backend/ (no network, no API keys, a few seconds):
    python scripts/evaluate_system.py --out ../docs/evaluation_results.md

1. Live pipeline latency: a synthetic 32-minute match of raw GSI (one payload
   per game second, as Dota sends it) through POST /gsi + GET
   /overlay/recommendation, in-process (FastAPI TestClient, no network).
2. Live advice on the two committed replay-derived matches (real games,
   one GSI-like state per second) through POST /demo/replay-state, which
   runs the real advice path on a simulated clock: how much advice, what
   kind, how much the scheduler suppressed.
3. Post-match review: sections, findings and blocks built from each data
   source (parsed replay, basic OpenDota, the app's own GSI recording) and
   the time to build them; the career over 26 matches.
4. AI coach fact check: clean sentences built from a match's facts must pass,
   and the same sentences with one fact changed (number, time, hero, item)
   must be caught. The model is not involved: this measures the guard itself.

Match data comes from tests/match_fixtures.py (schema-faithful synthetic
OpenDota matches and GSI streams) and data/match_simulations/ (real replays).
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import random
import re
import statistics
import subprocess
import sys
import tempfile
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent
os.environ["OPENDOTA_ENABLED"] = "false"
os.environ.setdefault("PLAYER_DATA_DIR", tempfile.mkdtemp(prefix="dota-ai-coach-eval-"))
sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(BACKEND_DIR / "tests"))

from fastapi.testclient import TestClient  # noqa: E402
from match_fixtures import (  # noqa: E402
    MATCH_ID,
    ME,
    FakeOpenDota,
    gsi_match_stream,
    opendota_match,
    recent_matches,
)

import app.logger as recommendation_logger  # noqa: E402
from app import gsi_state  # noqa: E402
from app.advice_scheduler import ADVICE_SCHEDULER  # noqa: E402
from app.coach_review import HERO_NAMES, FactChecker, match_facts  # noqa: E402
from app.coach_summary import COACH_SESSION_HISTORY  # noqa: E402
from app.main import _clear_demo_overlay_response, app  # noqa: E402
from app.match_memory import MATCH_MEMORY  # noqa: E402
from app.player_api import PLAYER_SERVICE  # noqa: E402

REPLAYS = {
    "Phantom Lancer 20-30 min (match 8843382732)": "replay_gsi_like_match_8843382732_pl_20_30.jsonl",
    "Juggernaut 10-20 min (match 8843471434)": "replay_gsi_like_match_8843471434_jugg_10_20.jsonl",
}
ITEMS = [
    "Battle Fury",
    "Black King Bar",
    "Manta Style",
    "Butterfly",
    "Maelstrom",
    "Desolator",
    "Skull Basher",
    "Abyssal Blade",
    "Satanic",
    "Daedalus",
    "Power Treads",
    "Mjollnir",
]


def reset_live_state() -> None:
    MATCH_MEMORY.reset()
    ADVICE_SCHEDULER.reset()
    COACH_SESSION_HISTORY.reset()
    _clear_demo_overlay_response()
    gsi_state._latest_raw_payload = None
    gsi_state._latest_normalized_state = None
    gsi_state._latest_timestamp = None
    gsi_state._previous_extra_context = None


def percentile(values: list[float], pct: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    index = min(len(ordered) - 1, max(0, round(pct / 100 * (len(ordered) - 1))))
    return ordered[index]


def timing_row(name: str, values_ms: list[float]) -> dict[str, Any]:
    return {
        "step": name,
        "n": len(values_ms),
        "mean_ms": round(statistics.fmean(values_ms), 2),
        "p50_ms": round(percentile(values_ms, 50), 2),
        "p95_ms": round(percentile(values_ms, 95), 2),
        "p99_ms": round(percentile(values_ms, 99), 2),
        "max_ms": round(max(values_ms), 2),
    }


# --- 1. live latency ---------------------------------------------------------------


WARM_UP_TICKS = 10


def evaluate_latency(client: TestClient) -> dict[str, Any]:
    reset_live_state()
    PLAYER_SERVICE.configure(Path(tempfile.mkdtemp()), client=None, auto_start=False)
    stream = gsi_match_stream(step_seconds=1, positions=True)
    # The first ticks load lazy data (knowledge base, hero tables); the last one
    # (POST_GAME) builds the post-match review: both are reported apart.
    for payload in stream[:WARM_UP_TICKS]:
        client.post("/gsi", json=payload)
        client.get("/overlay/recommendation?lang=ru")
    final = stream[-1]
    stream = stream[WARM_UP_TICKS:-1]
    gsi_ms: list[float] = []
    overlay_ms: list[float] = []
    for payload in stream:
        started = time.perf_counter()
        client.post("/gsi", json=payload)
        middle = time.perf_counter()
        client.get("/overlay/recommendation?lang=ru")
        done = time.perf_counter()
        gsi_ms.append((middle - started) * 1000)
        overlay_ms.append((done - middle) * 1000)
    total = [a + b for a, b in zip(gsi_ms, overlay_ms, strict=True)]
    started = time.perf_counter()
    client.post("/gsi", json=final)
    match_end_ms = (time.perf_counter() - started) * 1000
    return {
        "payloads": len(stream),
        "game_minutes": 32,
        "match_end_ms": round(match_end_ms, 1),
        "rows": [
            timing_row("POST /gsi", gsi_ms),
            timing_row("GET /overlay/recommendation", overlay_ms),
            timing_row("one tick (both)", total),
        ],
    }


# --- 2. advice on real replays ---------------------------------------------------------


def evaluate_replays(client: TestClient) -> list[dict[str, Any]]:
    results = []
    for label, file_name in REPLAYS.items():
        reset_live_state()
        path = REPO_ROOT / "data" / "match_simulations" / file_name
        states = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
        shown: list[dict[str, Any]] = []
        latencies = []
        for item in states:
            started = time.perf_counter()
            response = client.post(
                "/demo/replay-state",
                json={"timestamp_seconds": item["timestamp_seconds"], "state": item["state"]},
            ).json()["overlay"]
            latencies.append((time.perf_counter() - started) * 1000)
            if response.get("new_advice") and response.get("recommendation"):
                shown.append(response)
        stats = ADVICE_SCHEDULER.stats()
        minutes = (states[-1]["timestamp_seconds"] - states[0]["timestamp_seconds"]) / 60
        suppressed = {
            key: value
            for key, value in stats.items()
            if key.endswith("suppressed_count") and isinstance(value, int) and value
        }
        results.append(
            {
                "match": label,
                "states": len(states),
                "minutes": round(minutes, 1),
                "advice_shown": len(shown),
                "advice_per_10_min": round(len(shown) / minutes * 10, 1) if minutes else None,
                "urgent": sum(1 for r in shown if r.get("advice_mode") == "urgent"),
                "coaching": sum(1 for r in shown if r.get("advice_mode") == "coaching"),
                "decision_points": dict(Counter(r["decision_point"] for r in shown).most_common()),
                "min_gap_s": stats.get("min_game_time_gap_seconds"),
                "suppressed": suppressed,
                "suppressed_total": sum(suppressed.values()),
                "p95_ms": round(percentile(latencies, 95), 2),
                "examples": [
                    {
                        "t": r.get("simulated_time_label"),
                        "mode": r.get("advice_mode"),
                        "action": r["recommendation"].get("action"),
                    }
                    for r in shown[:4]
                ],
            }
        )
    return results


# --- 3. post-match review --------------------------------------------------------------


def _service(client: TestClient, matches: dict[int, dict[str, Any]], recent=None) -> None:
    PLAYER_SERVICE.configure(
        Path(tempfile.mkdtemp()),
        client=FakeOpenDota(matches=matches, recent=recent or []),
        auto_start=False,
    )
    client.post("/player/link", json={"steam": str(ME)})


def _review_row(label: str, detail: dict[str, Any], build_ms: float) -> dict[str, Any]:
    analysis = detail.get("analysis") or {}
    blocks = [name for name in ("build", "peers", "draft", "map") if analysis.get(name) is not None]
    return {
        "source": label,
        "score": (analysis.get("headline") or {}).get("score"),
        "sections": sorted((analysis.get("sections") or {}).keys()),
        "improvements": len(analysis.get("improvements") or []),
        "strengths": len(analysis.get("strengths") or []),
        "blocks": blocks,
        "series": sorted(k for k, v in (analysis.get("series") or {}).items() if v),
        "build_ms": round(build_ms, 1),
    }


def evaluate_reviews(client: TestClient) -> dict[str, Any]:
    rows = []
    for label, match in (
        ("OpenDota, parsed replay", opendota_match(good=False)),
        ("OpenDota, basic (not parsed)", opendota_match(good=False, parsed=False)),
    ):
        _service(client, {MATCH_ID: match})
        started = time.perf_counter()
        PLAYER_SERVICE.fetch_match(MATCH_ID, request_parse=False)
        PLAYER_SERVICE.jobs.run_pending(until=float("inf"))
        build_ms = (time.perf_counter() - started) * 1000
        rows.append(_review_row(label, client.get(f"/player/matches/{MATCH_ID}").json(), build_ms))

    reset_live_state()
    _service(client, {})
    PLAYER_SERVICE.client = None
    stream = gsi_match_stream(positions=True, win=False)
    for payload in stream[:-1]:
        client.post("/gsi", json=payload)
    started = time.perf_counter()
    client.post("/gsi", json=stream[-1])  # POST_GAME: the timeline is reviewed here
    build_ms = (time.perf_counter() - started) * 1000
    rows.append(
        _review_row(
            "GSI only (the app's own recording)",
            client.get(f"/player/matches/{MATCH_ID}").json(),
            build_ms,
        )
    )

    recent = recent_matches(26)
    matches = {
        r["match_id"]: opendota_match(good=r["radiant_win"], match_id=r["match_id"]) for r in recent
    }
    _service(client, matches, recent)
    PLAYER_SERVICE.request_sync()
    PLAYER_SERVICE.jobs.run_pending(until=float("inf"))
    started = time.perf_counter()
    career = client.get("/player/career?lang=ru").json()
    career_ms = (time.perf_counter() - started) * 1000
    return {
        "rows": rows,
        "career": {
            "matches": career.get("matches"),
            "analyzed": career.get("analyzed"),
            "focus_plan": len(career.get("focus_plan") or []),
            "self_compare": career.get("self_compare") is not None,
            "build_ms": round(career_ms, 1),
        },
    }


# --- 4. fact check --------------------------------------------------------------------

NUMBER_RE = re.compile(r"(?<![\d:.,])\d+(?:[.,]\d+)?(?![\d:])")
TIME_TOKEN_RE = re.compile(r"(?<![\d:])\d{1,2}:\d{2}(?!\d)")


def _sentences_from_facts(facts: dict[str, Any]) -> list[str]:
    """Clean sentences: the review's own finding texts plus lines built from the facts."""
    sentences: list[str] = []
    for finding in (facts.get("findings_to_improve") or []) + (
        facts.get("findings_strengths") or []
    ):
        sentences += [s.strip() for s in re.split(r"(?<=[.!?])\s+", finding["text"]) if s.strip()]
    for point in facts.get("every_5_minutes") or []:
        sentences.append(
            f"К {point['time']} у вас было {point['last_hits']} добиваний "
            f"при хорошем темпе {point['last_hits_good_pace']}."
        )
    sentences.append(f"На {facts['hero']} вы сделали {facts['gpm']} золота в минуту.")
    for section in (facts.get("sections") or {}).values():
        first = section.get("first_big_item") if isinstance(section, dict) else None
        if first:
            sentences.append(f"Первый большой предмет — {first['item']} к {first['time']}.")
    for item in facts.get("final_items") or facts.get("items") or []:
        if isinstance(item, str):
            sentences.append(f"В конце матча у вас был {item}.")
    return sentences


def _mutations(sentence: str, facts_text: str, rng: random.Random) -> list[tuple[str, str]]:
    """(kind, mutated sentence): one fact changed to a value the facts do not contain."""
    result = []
    numbers = [
        m for m in NUMBER_RE.finditer(sentence) if int(float(m.group().replace(",", "."))) > 12
    ]
    if numbers:
        match = rng.choice(numbers)
        value = float(match.group().replace(",", "."))
        for delta in (7, 13, 19, 23, 29, 31, 37):
            new = int(value + delta)
            if str(new) not in facts_text:
                result.append(
                    ("number", sentence[: match.start()] + str(new) + sentence[match.end() :])
                )
                break
        small = rng.randint(2, 12)
        result.append(
            ("small count 2-12", sentence[: match.start()] + str(small) + sentence[match.end() :])
        )
    times = list(TIME_TOKEN_RE.finditer(sentence))
    if times:
        match = rng.choice(times)
        minutes, seconds = map(int, match.group().split(":"))
        new = f"{minutes + 1}:{(seconds + 37) % 60:02d}"
        result.append(("time", sentence[: match.start()] + new + sentence[match.end() :]))
    for hero in HERO_NAMES:
        if hero in sentence:
            other = rng.choice([h for h in HERO_NAMES if h not in facts_text and len(h) > 3])
            result.append(("hero", sentence.replace(hero, other, 1)))
            break
    for item in ITEMS:
        if item in sentence:
            other = rng.choice([i for i in ITEMS if i not in facts_text])
            result.append(("item", sentence.replace(item, other, 1)))
            break
    return result


def evaluate_fact_check(client: TestClient, seed: int = 7) -> dict[str, Any]:
    rng = random.Random(seed)
    sentences: list[str] = []
    false_positives: list[str] = []
    mutated: list[tuple[str, str]] = []
    for good, lang in ((False, "ru"), (True, "ru"), (False, "en"), (True, "en")):
        _service(client, {MATCH_ID: opendota_match(good=good)})
        PLAYER_SERVICE.fetch_match(MATCH_ID, request_parse=False)
        PLAYER_SERVICE.jobs.run_pending(until=float("inf"))
        facts = match_facts(client.get(f"/player/matches/{MATCH_ID}?lang={lang}").json())
        if facts is None:
            continue
        facts_text = json.dumps(facts, ensure_ascii=False)
        checker = FactChecker(facts_text, ITEMS)
        clean = _sentences_from_facts(facts)
        sentences += [s for s in clean if not checker.problems(s)]
        false_positives += [s for s in clean if checker.problems(s)]
        for sentence in clean:
            for kind, text in _mutations(sentence, facts_text, rng):
                mutated.append((kind, "caught" if checker.problems(text) else "missed"))
    by_kind: dict[str, Counter] = {}
    for kind, outcome in mutated:
        by_kind.setdefault(kind, Counter())[outcome] += 1
    return {
        "clean_sentences": len(sentences) + len(false_positives),
        "clean_kept": len(sentences),
        "false_positive_examples": false_positives[:3],
        "mutations": {
            kind: {
                "n": sum(counts.values()),
                "caught": counts["caught"],
                "rate": round(counts["caught"] / sum(counts.values()), 3),
            }
            for kind, counts in sorted(by_kind.items())
        },
    }


# --- report ---------------------------------------------------------------------------


def _git_commit() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _table(rows: list[dict[str, Any]], columns: list[str]) -> str:
    lines = ["| " + " | ".join(columns) + " |", "|" + "---|" * len(columns)]
    for row in rows:
        cells = []
        for column in columns:
            value = row.get(column)
            if isinstance(value, list):
                value = ", ".join(str(v) for v in value) or "—"
            elif isinstance(value, dict):
                value = ", ".join(f"{k} {v}" for k, v in value.items()) or "—"
            cells.append("—" if value is None else str(value))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def to_markdown(result: dict[str, Any]) -> str:
    env = result["environment"]
    parts = [
        "# Evaluation results",
        "",
        f"Generated {env['generated_at']} by `backend/scripts/evaluate_system.py` "
        f"(commit {env['commit']}, Python {env['python']}, {env['platform']}). "
        "Explained in [EVALUATION.md](EVALUATION.md).",
        "",
        "## 1. Live pipeline latency",
        "",
        f"{result['latency']['payloads']} raw GSI payloads (a {result['latency']['game_minutes']}-minute "
        f"match, one per game second, after {WARM_UP_TICKS} warm-up ticks), in-process, ms:",
        "",
        _table(
            result["latency"]["rows"],
            ["step", "n", "mean_ms", "p50_ms", "p95_ms", "p99_ms", "max_ms"],
        ),
        "",
        "The POST_GAME payload, which records the match and builds its review: "
        f"{result['latency']['match_end_ms']} ms.",
        "",
        "## 2. Live advice on real replays (simulated clock)",
        "",
        _table(
            result["replays"],
            [
                "match",
                "states",
                "minutes",
                "advice_shown",
                "advice_per_10_min",
                "urgent",
                "coaching",
                "min_gap_s",
                "suppressed_total",
                "p95_ms",
            ],
        ),
        "",
    ]
    for replay in result["replays"]:
        parts += [
            f"**{replay['match']}** — decision points: "
            + ", ".join(f"{k} ×{v}" for k, v in replay["decision_points"].items()),
            "",
            "Suppressed by the scheduler: "
            + (", ".join(f"{k} {v}" for k, v in replay["suppressed"].items()) or "—"),
            "",
            "First advice shown:",
            "",
            *[f"- {e['t']} ({e['mode']}): {e['action']}" for e in replay["examples"]],
            "",
        ]
    reviews = result["reviews"]
    parts += [
        "## 3. Post-match review",
        "",
        _table(
            reviews["rows"],
            [
                "source",
                "score",
                "sections",
                "improvements",
                "strengths",
                "blocks",
                "series",
                "build_ms",
            ],
        ),
        "",
        "Career over {matches} matches ({analyzed} reviewed): focus plan {focus_plan} items, "
        "best-vs-worst comparison: {self_compare}, built in {build_ms} ms.".format(
            **reviews["career"]
        ),
        "",
        "## 4. AI coach fact check",
        "",
        f"Clean sentences kept: {result['fact_check']['clean_kept']} of "
        f"{result['fact_check']['clean_sentences']}.",
        "",
        _table(
            [{"changed fact": k, **v} for k, v in result["fact_check"]["mutations"].items()],
            ["changed fact", "n", "caught", "rate"],
        ),
        "",
    ]
    return "\n".join(parts)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--out", type=Path, help="write the markdown report here")
    parser.add_argument("--json", type=Path, help="write the raw numbers here")
    args = parser.parse_args()

    recommendation_logger.LOGS_DIR = Path(tempfile.mkdtemp(prefix="dota-ai-coach-eval-logs-"))
    client = TestClient(app)
    result = {
        "environment": {
            "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "commit": _git_commit(),
            "python": platform.python_version(),
            "platform": platform.platform(terse=True),
        },
        "latency": evaluate_latency(client),
        "replays": evaluate_replays(client),
        "reviews": evaluate_reviews(client),
        "fact_check": evaluate_fact_check(client),
    }
    report = to_markdown(result)
    if args.out:
        args.out.write_text(report + "\n", encoding="utf-8")
    if args.json:
        args.json.write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    print(report)


if __name__ == "__main__":
    main()
