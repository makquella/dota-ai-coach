"""
compare_coach_models.py - run one match through several AI coach models.

Same facts, same prompt, same fact check as the app; prints a table (time,
attempts, share of text dropped by the fact check, errors) and writes every
review side by side to a Markdown file for reading.

Keys come from the env: GEMINI_API_KEY, OPENROUTER_API_KEY, GROQ_API_KEY.

    cd backend
    GEMINI_API_KEY=... OPENROUTER_API_KEY=... python scripts/compare_coach_models.py \\
        --model gemini:gemini-3.8-flash --model openrouter:stealth/space-bunny-alpha \\
        --lang uk --out coach_compare.md

By default the synthetic test match is used (tests/match_fixtures.py). With
--data-dir (the app's PLAYER_DATA_DIR, e.g. %APPDATA%\\DotaAICoach\\player_data)
and --match, a real match of the linked player is reviewed instead;
--career reviews the recent matches instead of one match.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.analysis_texts import render_analysis  # noqa: E402
from app.coach_llm import PROVIDERS, CoachLLM, CoachLLMError, settings_from  # noqa: E402
from app.coach_review import (  # noqa: E402
    career_facts,
    match_facts,
    recent_match_line,
    review_career,
    review_match,
)
from app.player_service import PlayerService  # noqa: E402

KEY_ENV = {"gemini": "GEMINI_API_KEY", "openrouter": "OPENROUTER_API_KEY", "groq": "GROQ_API_KEY"}


def _service(args: argparse.Namespace) -> tuple[PlayerService, int]:
    if args.data_dir:
        # Work on a copy: the app's database is never changed.
        copy = Path(tempfile.mkdtemp()) / "player_data"
        shutil.copytree(args.data_dir, copy)
        service = PlayerService(copy, client=None, auto_start=False)
        if not args.match and not args.career:
            sys.exit("--match is required with --data-dir (or use --career)")
        return service, int(args.match or 0)
    sys.path.insert(0, str(BACKEND_DIR / "tests"))
    from match_fixtures import (
        MATCH_ID,
        ME,
        FakeOpenDota,
        opendota_match,
        recent_matches,
    )

    recent = recent_matches(12)
    matches = {
        r["match_id"]: opendota_match(good=r["radiant_win"], match_id=r["match_id"]) for r in recent
    }
    matches[MATCH_ID] = opendota_match(good=False)
    service = PlayerService(
        tempfile.mkdtemp(), client=FakeOpenDota(matches=matches, recent=recent), auto_start=False
    )
    service.link(str(ME))
    service.jobs.run_pending(until=float("inf"))
    service.client = None
    return service, MATCH_ID


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--model", action="append", required=True, help="provider:model")
    parser.add_argument("--lang", default="uk", choices=("uk", "en"))
    parser.add_argument("--career", action="store_true", help="review the recent matches")
    parser.add_argument("--data-dir", help="the app's PLAYER_DATA_DIR (a copy is used)")
    parser.add_argument("--match", help="match id (with --data-dir)")
    parser.add_argument("--out", default="coach_compare.md")
    args = parser.parse_args()

    service, match_id = _service(args)
    account = service.store.primary_account_id()
    if args.career:
        career = service.career(args.lang)
        lines = [
            recent_match_line(render_analysis(m["analysis"], args.lang))
            for m in service.store.matches_for_career(account or 0)
            if m.get("analysis")
        ]
        facts = career_facts(career, lines)
        generate = review_career
    else:
        detail = service.match_detail(match_id, args.lang)
        facts = match_facts(detail) if detail else None
        generate = review_match
    if not facts:
        sys.exit("No reviewed data for this match / player.")

    rows, sections = [], []
    for spec in args.model:
        provider, _, model = spec.partition(":")
        key = os.environ.get(KEY_ENV.get(provider, ""), "")
        settings = settings_from(
            {"provider": provider, "api_key": key, "model": model}, source="env"
        )
        if provider not in PROVIDERS or settings is None:
            rows.append((spec, "-", "-", "-", f"no {KEY_ENV.get(provider, 'provider')}"))
            continue
        llm = CoachLLM(settings, fallbacks=False)
        started = time.time()
        try:
            result = generate(llm, facts, args.lang, known_items=service._known_items())
        except CoachLLMError as error:
            rows.append((spec, f"{time.time() - started:.0f} s", "-", "-", error.code))
            sections.append(f"## {spec}\n\nError: `{error.code}` {error}\n")
            continue
        review = result["review"]
        total = len(json.dumps(review, ensure_ascii=False)) + result["dropped_chars"]
        dropped = f"{100 * result['dropped_chars'] / max(1, total):.0f}%"
        rows.append(
            (spec, f"{time.time() - started:.0f} s", str(result["attempts"]), dropped, "ok")
        )
        sections.append(
            f"## {spec}\n\n```json\n{json.dumps(review, ensure_ascii=False, indent=1)}\n```\n"
        )

    table = [
        "| model | time | attempts | dropped by fact check | result |",
        "|---|---|---|---|---|",
    ]
    table += [f"| {' | '.join(row)} |" for row in rows]
    print("\n".join(table))
    Path(args.out).write_text("\n".join(table) + "\n\n" + "\n".join(sections), encoding="utf-8")
    print(f"\nReviews: {args.out}")


if __name__ == "__main__":
    main()
