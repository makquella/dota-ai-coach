"""Which video to make next: a format and a topic, from the data and the history.

  - a published release not promoted yet goes first (within RELEASE_DAYS of its publication);
  - the week's meta and its fact once per meta post;
  - coach and hero videos rotate heroes with a site page, the week's popular
    heroes first, none of the last HERO_REPEAT videos' heroes;
  - draft videos rotate the enemies the app counters with an item (the
    format TikTok gets first: the highest weight), none of the last
    DRAFT_REPEAT draft videos' enemies;
  - the format is drawn by weight (WEIGHTS, times what the statistics say works,
    data/promo/weights.json), never the same format twice in a row.

The draw is seeded by the date, so a re-run of the same day picks the same."""

from __future__ import annotations

import json
import os
import random
import urllib.request
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
HISTORY = ROOT / "data" / "promo" / "history.json"
WEIGHTS_FILE = ROOT / "data" / "promo" / "weights.json"
NOTES = ROOT / "docs" / "release-notes"
REPOSITORY = "makquella/wardly"
USER_AGENT = "Wardly promo"

WEIGHTS = {"draft": 6.0, "coach": 3.0, "hero": 2.0, "meta": 2.0, "fact": 1.0, "release": 5.0}
DRAFT_REPEAT = 8
HERO_REPEAT = 20
RELEASE_DAYS = 10
MIN_WEIGHT, MAX_WEIGHT = 0.3, 3.0  # what the statistics may do to a base weight


@dataclass
class Choice:
    format: str
    topic: str
    data: dict[str, Any]


def load_history() -> list[dict[str, Any]]:
    if not HISTORY.exists():
        return []
    return list(json.loads(HISTORY.read_text(encoding="utf-8")))


def save_history(history: list[dict[str, Any]]) -> None:
    HISTORY.parent.mkdir(parents=True, exist_ok=True)
    HISTORY.write_text(
        json.dumps(history[-200:], ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8",
    )


def load_weights() -> dict[str, float]:
    """Base weights times the multipliers learned from the statistics (bounded)."""
    weights = dict(WEIGHTS)
    if WEIGHTS_FILE.exists():
        learned = json.loads(WEIGHTS_FILE.read_text(encoding="utf-8")).get("multipliers", {})
        for name, factor in learned.items():
            if name in weights and isinstance(factor, (int, float)):
                weights[name] *= min(MAX_WEIGHT, max(MIN_WEIGHT, float(factor)))
    return weights


def _done(history: list[dict[str, Any]], fmt: str, topic: str) -> bool:
    return any(h.get("format") == fmt and h.get("topic") == topic for h in history)


def published_releases() -> dict[str, date]:
    """{"v<version>": publication date} of the repository's published GitHub
    Releases. The Release workflow pushes or creates the tag before the
    installer is built, smoke-tested and the release published, so a tag alone
    does not mean anyone can download the version. {} when GitHub cannot be
    asked: then no release video is made."""
    repository = os.environ.get("GITHUB_REPOSITORY", "").strip() or REPOSITORY
    headers = {"Accept": "application/vnd.github+json", "User-Agent": USER_AGENT}
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(
        f"https://api.github.com/repos/{repository}/releases?per_page=30", headers=headers
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
            releases = json.loads(response.read())
    except (OSError, ValueError):
        return {}
    published: dict[str, date] = {}
    for release in releases if isinstance(releases, list) else []:
        stamp = release.get("published_at") if isinstance(release, dict) else None
        if not stamp or release.get("draft") or release.get("prerelease"):
            continue
        try:
            published[str(release.get("tag_name"))] = date.fromisoformat(str(stamp)[:10])
        except ValueError:
            continue
    return published


def latest_release(today: date) -> tuple[str, str] | None:
    """(version, notes) of the newest published GitHub Release within RELEASE_DAYS
    of its publication.

    Release notes land on main before the installer is published; a video about
    a version nobody can download yet would send viewers to the old one."""
    files = sorted(
        NOTES.glob("v*.md"),
        key=lambda p: tuple(int(x) for x in p.stem[1:].split(".") if x.isdigit()),
    )
    releases = published_releases() if files else {}
    for notes in reversed(files):
        published = releases.get(notes.stem)
        if published is None:
            continue
        if (today - published).days > RELEASE_DAYS:
            return None
        return notes.stem[1:], notes.read_text(encoding="utf-8")
    return None


def hero_order(
    site_heroes: list[dict[str, Any]], week: dict[str, Any] | None
) -> list[dict[str, Any]]:
    """Site heroes, the week's most picked first (a wider audience knows them)."""
    pick = {}
    if week:
        matches = sum(h["picks"] for h in week["heroes"]) / 10 or 1
        pick = {h.get("key"): h["picks"] / matches for h in week["heroes"] if h.get("key")}
    return sorted(site_heroes, key=lambda h: pick.get(h["key"], 0), reverse=True)


def next_hero(
    site_heroes: list[dict[str, Any]],
    week: dict[str, Any] | None,
    history: list[dict[str, Any]],
    rng: random.Random,
) -> dict[str, Any]:
    recent = {h["topic"] for h in history[-HERO_REPEAT:] if h.get("format") in ("coach", "hero")}
    fresh = [h for h in hero_order(site_heroes, week) if h["key"] not in recent] or site_heroes
    # Among the ten most popular fresh heroes, by chance: not always the same top one.
    return rng.choice(fresh[:10])


def next_enemy(
    enemies: list[str],
    keys: dict[str, str | None],
    history: list[dict[str, Any]],
    rng: random.Random,
) -> str | None:
    """An enemy hero for a draft video, none of the last DRAFT_REPEAT draft videos'."""
    drafts = [h for h in history if h.get("format") == "draft"][-DRAFT_REPEAT:]
    recent = {h.get("topic") for h in drafts}
    fresh = [e for e in enemies if keys.get(e) not in recent] or enemies
    return rng.choice(fresh) if fresh else None


def choose(
    today: date,
    site_heroes: list[dict[str, Any]],
    week: dict[str, Any] | None,
    history: list[dict[str, Any]],
    weights: dict[str, float] | None = None,
    forced: str | None = None,
) -> Choice:
    rng = random.Random(today.isoformat())
    weights = weights or load_weights()
    options: dict[str, Choice] = {}

    release = latest_release(today)
    if release and not _done(history, "release", release[0]):
        options["release"] = Choice(
            "release", release[0], {"version": release[0], "notes": release[1]}
        )
    if week and not _done(history, "meta", week["date"]):
        options["meta"] = Choice("meta", week["date"], {"week": week})
    if week and not any(
        h.get("format") == "fact" and str(h.get("topic", "")).startswith(week["date"])
        for h in history
    ):
        options["fact"] = Choice("fact", week["date"], {"week": week})
    from . import draft_demo

    pool = draft_demo.enemies()
    enemy = next_enemy(pool, {e: draft_demo.hero_key(e) for e in pool}, history, rng)
    found = draft_demo.card(enemy) if enemy else None
    if found:
        options["draft"] = Choice("draft", found["key"], found)
    hero = next_hero(site_heroes, week, history, rng)
    options["coach"] = Choice("coach", hero["key"], {"hero": hero})
    options["hero"] = Choice("hero", hero["key"], {"hero": hero})

    if forced:
        if forced not in options:
            raise SystemExit(f"nothing to make for format {forced!r} now")
        return options[forced]
    if "release" in options:
        return options["release"]
    last = history[-1]["format"] if history else None
    names = [name for name in options if name != last] or list(options)
    return options[rng.choices(names, weights=[weights.get(n, 1.0) for n in names])[0]]
