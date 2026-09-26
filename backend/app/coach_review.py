"""
coach_review.py - AI coach texts on top of the rule-based reviews.

The rules (post_match_analysis, career_analysis) stay the source of every
number and conclusion. This module turns their output into a compact JSON of
facts, asks the model to explain the match (or the last matches) like a coach
watching the replay, and checks the answer before it is shown:

- shape: the expected JSON fields, sizes, no markdown;
- facts: every number, hero and item in the text must be present in the facts
  (plus small counts and minute marks). Sentences that fail are dropped; if
  too much is lost the model gets one retry with the list of offending
  tokens, then the answer is rejected.

Nothing here touches the live advice path.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from app.analysis_texts import clock
from app.coach_llm import CoachLLMError, parse_json_object
from app.dota_constants import HEROES

COACH_VERSION = 1
# Share of the text that may be dropped by the fact check before a retry.
MAX_SCRUBBED_SHARE = 0.25
# Small counts ("3 deaths") are always allowed; minute marks ("by minute 15",
# "15:00") only as minutes, so "50 last hits" still has to come from the facts.
ALWAYS_ALLOWED_NUMBERS = {float(n) for n in range(13)} | {100.0}
MINUTE_RE = re.compile(
    r"(?<![\d:.,])(\d{1,2})(?:-?(?:й|я|ю|ой|ей|th))?\s+(?:минут\w*|мин\b|minutes?\b|min\b)"
    r"|\bminute\s+(\d{1,2})\b",
    re.IGNORECASE,
)

HERO_NAMES = sorted({name for name, _ in HEROES.values()}, key=len, reverse=True)

LANGUAGE_RULES = {
    "ru": (
        "Write in Russian. Address the player formally («вы»). Keep hero and item names "
        "in English exactly as in the data; no other English words (use the Russian words "
        "players use: фарм, линия, добивания, крипы, лес, тайминг, ценность for net worth; GPM "
        "and XPM stay). Times as «к 26:00»."
    ),
    "en": "Write in English. Address the player as «you».",
}

COMMON_RULES = """Rules:
- Use only the facts in the JSON. Every number, time, hero and item you mention must appear in the JSON. Do not calculate new numbers and do not invent events, positions, teammates' mistakes or draft ideas that the data does not show.
- The "findings" come from exact rules. You may merge, reorder or connect them, never contradict them.
- Think like a coach watching the replay: connect the facts into causes and effects, name the one or two things that decided the game for the player, and say what to do differently in concrete terms (time, hero, item, map action).
- No generic filler such as "play better" or "watch the minimap" unless it is tied to a specific fact.
- Calm, direct and honest; praise only what the data supports. No emoji, no markdown, no lists inside strings.
- Answer with one JSON object only."""

MATCH_SCHEMA = """JSON format:
{
  "summary": "2-4 sentences: what decided this game for the player",
  "turning_points": [{"time": "mm:ss", "text": "what happened and why it mattered"}],  // 1-4, times from the data
  "mistakes": [{"title": "short title", "detail": "what went wrong, with facts", "fix": "what to do next time"}],  // 1-3, most important first
  "strengths": ["one sentence each"],  // 0-2
  "next_game": ["one concrete goal each"]  // 2-3
}"""

CAREER_SCHEMA = """JSON format:
{
  "summary": "2-4 sentences: where the player stands and what holds them back",
  "patterns": [{"title": "short title", "detail": "the recurring problem, with facts", "fix": "how to train it"}],  // 1-3, most important first
  "strengths": ["one sentence each"],  // 0-2
  "plan": ["one concrete goal for the next games each"]  // 2-3
}"""

MATCH_SYSTEM = (
    "You are an experienced Dota 2 coach reviewing one match of your student (the player). "
    "The JSON holds the facts of the match computed from the replay or the game's telemetry.\n\n"
    + COMMON_RULES
    + "\n\n"
    + MATCH_SCHEMA
)

CAREER_SYSTEM = (
    "You are an experienced Dota 2 coach reviewing the recent matches of your student (the "
    "player). The JSON holds statistics and recurring findings computed by exact rules.\n\n"
    + COMMON_RULES
    + "\n\n"
    + CAREER_SCHEMA
)

LIMITS = {"summary": 700, "title": 80, "detail": 450, "fix": 320, "line": 260}


# --- facts for the model ------------------------------------------------------------


def match_facts(detail: dict[str, Any]) -> dict[str, Any] | None:
    """Compact facts of one match from the rendered review (no account ids or names)."""
    analysis = detail.get("analysis")
    if not analysis:
        return None
    headline = analysis.get("headline") or {}
    sources = analysis.get("sources") or []
    facts: dict[str, Any] = {
        "hero": headline.get("hero"),
        "role": analysis.get("role_label") or analysis.get("role"),
        "result": _result(headline.get("win")),
        "duration": clock(headline.get("duration")),
        "kills_deaths_assists": _kda(headline),
        "gpm": headline.get("gpm"),
        "xpm": headline.get("xpm"),
        "last_hits": headline.get("last_hits"),
        "denies": headline.get("denies"),
        "net_worth": headline.get("net_worth"),
        "hero_damage": headline.get("hero_damage"),
        "review_score_of_100": headline.get("score"),
        "data": "parsed replay"
        if analysis.get("parsed")
        else ("OpenDota summary" if "opendota" in sources else "the app's live recording"),
        "sections": {
            (section.get("label") or name): _section_facts(section)
            for name, section in (analysis.get("sections") or {}).items()
        },
        "findings_to_improve": [
            _finding(f, with_drill=True) for f in analysis.get("improvements") or []
        ],
        "findings_strengths": [_finding(f) for f in analysis.get("strengths") or []],
        "every_5_minutes": _series(analysis.get("series") or {}),
        "events": [_event(m) for m in analysis.get("moments") or []],
    }
    peers = analysis.get("peers")
    if peers and peers.get("peers"):
        facts["rank"] = peers.get("lobby_rank_label")
        facts["same_role_opponent"] = _peer_facts(peers)
    build = analysis.get("build")
    if build:
        facts["build"] = _build_facts(build)
    scoreboard = detail.get("scoreboard")
    if scoreboard:
        mine = next((row for row in scoreboard if row.get("me")), None)
        side = mine.get("is_radiant") if mine else True
        facts["your_team"] = [_score_row(r) for r in scoreboard if r.get("is_radiant") == side]
        facts["enemy_team"] = [_score_row(r) for r in scoreboard if r.get("is_radiant") != side]
    return _prune(facts)


def career_facts(career: dict[str, Any], recent: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Facts over the recent matches; `recent` = rendered reviews, newest first."""
    if not career.get("linked") or not career.get("analyzed"):
        return None
    facts: dict[str, Any] = {
        "matches": career.get("matches"),
        "reviewed_matches": career.get("analyzed"),
        "winrate_percent": career.get("winrate"),
        "averages": career.get("averages"),
        "last_10_vs_previous_10": {
            key: {k: v for k, v in value.items() if k in ("recent", "previous", "delta")}
            for key, value in (career.get("trend") or {}).items()
            if isinstance(value, dict)
        },
        "heroes": [
            {
                "hero": row.get("hero"),
                "matches": row.get("matches"),
                "winrate_percent": row.get("winrate"),
                "hero_winrate_at_your_rank_percent": row.get("bracket_winrate"),
            }
            for row in (career.get("heroes") or [])[:6]
        ],
        "recurring_problems": [
            {"title": r.get("title"), "in_matches": f"{r.get('count')} of {r.get('of')}"}
            for r in career.get("recurring") or []
        ],
        "recurring_strengths": [
            {"title": r.get("title"), "in_matches": f"{r.get('count')} of {r.get('of')}"}
            for r in career.get("recurring_strengths") or []
        ],
        "recent_matches": recent[:10],
    }
    rank = career.get("rank")
    if rank:
        facts["rank"] = rank.get("rank_label")
        facts["role"] = rank.get("role_label")
        facts["you_vs_same_role_players_of_your_rank"] = [
            {"metric": row["key"], "you": row["you"], "them": row["peers"], "diff": row["diff"]}
            for row in rank.get("metrics") or []
        ]
    return _prune(facts)


def recent_match_line(analysis: dict[str, Any]) -> dict[str, Any]:
    """One rendered review -> a line of the career facts."""
    headline = analysis.get("headline") or {}
    return _prune(
        {
            "hero": headline.get("hero"),
            "result": _result(headline.get("win")),
            "duration": clock(headline.get("duration")),
            "kills_deaths_assists": _kda(headline),
            "gpm": headline.get("gpm"),
            "review_score_of_100": headline.get("score"),
            "main_problems": [f.get("title") for f in (analysis.get("improvements") or [])[:3]],
        }
    )


def facts_hash(facts: dict[str, Any], lang: str) -> str:
    raw = json.dumps({"v": COACH_VERSION, "lang": lang, "facts": facts}, sort_keys=True)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


# --- generation ---------------------------------------------------------------------


def review_match(
    llm: Any, facts: dict[str, Any], lang: str, *, known_items: list[str] | None = None
) -> dict[str, Any]:
    return _generate(llm, MATCH_SYSTEM, facts, lang, _normalize_match, known_items)


def review_career(
    llm: Any, facts: dict[str, Any], lang: str, *, known_items: list[str] | None = None
) -> dict[str, Any]:
    return _generate(llm, CAREER_SYSTEM, facts, lang, _normalize_career, known_items)


def _generate(
    llm: Any,
    system: str,
    facts: dict[str, Any],
    lang: str,
    normalize: Any,
    known_items: list[str] | None,
) -> dict[str, Any]:
    facts_text = json.dumps(facts, ensure_ascii=False)
    checker = FactChecker(facts_text, known_items or [])
    messages = [
        {"role": "system", "content": system + "\n\n" + LANGUAGE_RULES[lang]},
        {"role": "user", "content": facts_text},
    ]
    last_problems: list[str] = []
    for attempt in range(2):
        content = llm.complete(messages)
        try:
            review = normalize(parse_json_object(content))
        except CoachLLMError:
            if attempt == 0:
                messages = [
                    *messages,
                    {"role": "assistant", "content": content[:2000]},
                    {"role": "user", "content": "Answer with the JSON object only."},
                ]
                continue
            raise
        scrubbed, dropped, total, problems = checker.scrub(review)
        valid = scrubbed is not None and normalize_ok(scrubbed)
        if valid and (dropped <= MAX_SCRUBBED_SHARE * total or attempt == 1):
            return {"review": scrubbed, "dropped_chars": dropped, "attempts": attempt + 1}
        last_problems = problems
        messages = [
            *messages,
            {"role": "assistant", "content": content[:4000]},
            {
                "role": "user",
                "content": (
                    "Your answer mentions things that are not in the data: "
                    + ", ".join(problems[:12])
                    + ". Rewrite the whole answer using only numbers, times, heroes and items "
                    "from the JSON. Same JSON format."
                ),
            },
        ]
    raise CoachLLMError("unverified", "; ".join(last_problems[:12]))


def normalize_ok(review: dict[str, Any]) -> bool:
    if not review.get("summary"):
        return False
    if "mistakes" in review:
        return bool(review["mistakes"]) and bool(review.get("next_game"))
    return bool(review.get("patterns")) and bool(review.get("plan"))


def _normalize_match(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "summary": _text(data.get("summary"), LIMITS["summary"]),
        "turning_points": [
            {"time": _time(tp.get("time")), "text": _text(tp.get("text"), LIMITS["line"])}
            for tp in _dicts(data.get("turning_points"))[:4]
            if _time(tp.get("time")) and _text(tp.get("text"), LIMITS["line"])
        ],
        "mistakes": _blocks(data.get("mistakes")),
        "strengths": _lines(data.get("strengths"), 2),
        "next_game": _lines(data.get("next_game"), 3),
    }


def _normalize_career(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "summary": _text(data.get("summary"), LIMITS["summary"]),
        "patterns": _blocks(data.get("patterns")),
        "strengths": _lines(data.get("strengths"), 2),
        "plan": _lines(data.get("plan"), 3),
    }


# --- fact check -------------------------------------------------------------------


class FactChecker:
    """Numbers, heroes and items of a text must appear in the facts."""

    def __init__(self, facts_text: str, known_items: list[str]) -> None:
        self.facts_text = facts_text
        self.allowed = set(ALWAYS_ALLOWED_NUMBERS)
        self.times = {f"{m}:00" for m in range(0, 91, 5)}
        self.times |= {_plain_time(t) for t in TIME_RE.findall(facts_text)}
        for value in _numbers(TIME_RE.sub(" ", facts_text)):
            self.allowed |= {value, float(round(value)), round(value, 1)}
            if 0 < value < 1:
                self.allowed.add(float(round(value * 100)))
            if value >= 1000:
                # Rounded big numbers ("11.5k", "14 тыс") are parsed back to 11500 / 14000.
                self.allowed |= {round(value, -2), round(value, -3)}
        names = [n for n in HERO_NAMES] + sorted(
            {i for i in known_items if len(i) >= 4}, key=len, reverse=True
        )
        self.names = [n for n in names if n not in facts_text]
        self._name_re = (
            re.compile(r"(?<!\w)(" + "|".join(re.escape(n) for n in self.names) + r")(?!\w)")
            if self.names
            else None
        )

    def problems(self, text: str) -> list[str]:
        found = [t for t in TIME_RE.findall(text) if _plain_time(t) not in self.times]
        text = MINUTE_RE.sub(_minute_mark, TIME_RE.sub(" ", text))
        for value in _numbers(text):
            if not any(abs(value - a) < 0.051 for a in self.allowed):
                found.append(_format_number(value))
        if self._name_re:
            found += self._name_re.findall(text)
        return found

    def scrub(self, review: dict[str, Any]) -> tuple[dict[str, Any] | None, int, int, list[str]]:
        """Drop sentences with unknown facts. -> (review, dropped chars, total chars, problems)."""
        dropped = total = 0
        problems: list[str] = []

        def clean(text: str) -> str:
            nonlocal dropped, total
            total += len(text)
            kept = []
            for sentence in _sentences(text):
                bad = self.problems(sentence)
                if bad:
                    problems.extend(bad)
                    dropped += len(sentence)
                else:
                    kept.append(sentence)
            return " ".join(kept).strip()

        result: dict[str, Any] = {}
        for key, value in review.items():
            if isinstance(value, str):
                result[key] = clean(value)
            elif isinstance(value, list):
                items: list[Any] = []
                for item in value:
                    if isinstance(item, str):
                        text = clean(item)
                        if text:
                            items.append(text)
                    elif isinstance(item, dict):
                        cleaned = {k: clean(v) if k != "time" else v for k, v in item.items()}
                        if "time" in cleaned and self.problems(cleaned["time"]):
                            problems.append(cleaned["time"])
                            continue
                        main = cleaned.get("text") or cleaned.get("detail")
                        if main and ("title" not in item or cleaned.get("title")):
                            items.append(cleaned)
                result[key] = items
        return result, dropped, total, sorted(set(problems))


# --- helpers ------------------------------------------------------------------------


TIME_RE = re.compile(r"(?<![\d:])\d{1,2}:\d{2}(?![\d:])")
THOUSANDS_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:k|тыс\.?)(?!\w)", re.IGNORECASE)


def _minute_mark(match: re.Match[str]) -> str:
    """ "15-й минуте" / "by minute 20": a 5-minute mark needs no fact."""
    minutes = int(match.group(1) or match.group(2))
    return " " if minutes % 5 == 0 and minutes <= 90 else match.group(0)


def _plain_time(value: str) -> str:
    minutes, seconds = value.split(":")
    return f"{int(minutes)}:{seconds}"


def _numbers(text: str) -> list[float]:
    # "11 500" / "11,500" -> 11500; "2,4" -> 2.4; "11.5k" / "11,5 тыс" -> 11500.
    # Not Cyrillic "к": in Russian it also means "by" ("к 26:00").
    text = re.sub(r"(?<=\d)[ \u00a0\u202f](?=\d{3}(?!\d))", "", text)
    text = re.sub(r"(?<=\d),(?=\d{3}(?!\d))", "", text)
    text = re.sub(r"(?<=\d),(?=\d)", ".", text)
    values = [float(m) * 1000 for m in THOUSANDS_RE.findall(text)]
    text = THOUSANDS_RE.sub(" ", text)
    return values + [float(m) for m in re.findall(r"\d+(?:\.\d+)?", text)]


def _format_number(value: float) -> str:
    return str(int(value)) if value == int(value) else str(value)


def _sentences(text: str) -> list[str]:
    return [s for s in re.split(r"(?<=[.!?…])\s+", text.strip()) if s]


def _text(value: Any, limit: int) -> str:
    if not isinstance(value, str):
        return ""
    text = re.sub(r"[*_`#]+", "", value)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    cut = text[:limit]
    end = max(cut.rfind(". "), cut.rfind("! "), cut.rfind("? "))
    return cut[: end + 1] if end > limit // 2 else cut.rstrip() + "…"


def _time(value: Any) -> str:
    text = str(value or "").strip()
    match = re.fullmatch(r"(\d{1,2}):(\d{2})", text)
    return f"{int(match.group(1))}:{match.group(2)}" if match else ""


def _dicts(value: Any) -> list[dict[str, Any]]:
    return [v for v in value if isinstance(v, dict)] if isinstance(value, list) else []


def _lines(value: Any, limit: int) -> list[str]:
    if not isinstance(value, list):
        return []
    lines = [_text(v, LIMITS["line"]) for v in value]
    return [line for line in lines if line][:limit]


def _blocks(value: Any) -> list[dict[str, str]]:
    blocks = []
    for item in _dicts(value)[:3]:
        block = {
            "title": _text(item.get("title"), LIMITS["title"]),
            "detail": _text(item.get("detail"), LIMITS["detail"]),
            "fix": _text(item.get("fix"), LIMITS["fix"]),
        }
        if block["title"] and block["detail"]:
            blocks.append(block)
    return blocks


def _result(win: Any) -> str:
    return "unknown" if win is None else ("win" if win else "loss")


def _kda(headline: dict[str, Any]) -> str:
    return f"{headline.get('kills')}/{headline.get('deaths')}/{headline.get('assists')}"


def _finding(finding: dict[str, Any], *, with_drill: bool = False) -> dict[str, Any]:
    row = {
        "area": finding.get("section_label"),
        "title": finding.get("title"),
        "text": finding.get("text"),
    }
    if with_drill:
        row["drill"] = finding.get("drill")
    return row


def _section_facts(section: dict[str, Any]) -> dict[str, Any]:
    skip = {"label", "rating", "big_items", "first_item"}
    row = {k: v for k, v in section.items() if k not in skip and not isinstance(v, (dict, list))}
    first = section.get("first_item")
    if isinstance(first, dict):
        row["first_big_item"] = {"item": first.get("item"), "time": clock(first.get("t"))}
    if "time_dead" in row:
        row["time_dead"] = clock(row["time_dead"])
    return row


def _series(series: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    minutes = series.get("minutes") or []
    for minute in minutes:
        if minute == 0 or minute % 5:
            continue
        row: dict[str, Any] = {"time": clock(minute * 60)}
        for key, name in (
            ("last_hits", "last_hits"),
            ("last_hits_target", "last_hits_good_pace"),
            ("gold", "gold"),
            ("xp", "xp"),
        ):
            values = series.get(key) or []
            if minute < len(values) and values[minute] is not None:
                row[name] = values[minute]
        rows.append(row)
    return rows


def _event(moment: dict[str, Any]) -> dict[str, Any]:
    row: dict[str, Any] = {"time": clock(moment.get("t")), "event": moment.get("type")}
    if moment.get("type") == "death":
        row["killed_by"] = moment.get("killer")
        row["unspent_gold"] = moment.get("gold")
    elif moment.get("type") == "item":
        row["item"] = moment.get("item")
    elif moment.get("type") == "farm_stall":
        row["until"] = clock(moment.get("to"))
    return row


def _peer_facts(peers: dict[str, Any]) -> dict[str, Any]:
    opponent = peers["peers"][0]
    me, them = peers.get("me") or {}, opponent.get("metrics") or {}
    metrics = []
    for key in ("gpm", "xpm", "lh_10", "deaths", "kda", "damage_per_min", "net_worth"):
        if me.get(key) is None or them.get(key) is None:
            continue
        metrics.append(
            {
                "metric": "last_hits_at_10:00" if key == "lh_10" else key,
                "you": me[key],
                "them": them[key],
                "diff": round(me[key] - them[key], 2),
            }
        )
    return {
        "hero": opponent.get("hero"),
        "enemy": opponent.get("enemy"),
        "role": peers.get("role_label"),
        "metrics": metrics,
    }


def _build_facts(build: dict[str, Any]) -> dict[str, Any]:
    items = []
    for item in build.get("items") or []:
        row: dict[str, Any] = {"item": item.get("name"), "bought_at": clock(item.get("t"))}
        timing = item.get("timing")
        if timing:
            row["hero_winrate_when_bought_by"] = {
                clock(b["time"]): f"{b['winrate']}%" for b in timing.get("buckets") or []
            }
            row["usual_timing"] = clock(timing.get("typical_bucket"))
        items.append(row)
    popular = build.get("popular") or {}
    return {
        "your_items": items,
        "pro_core_items": [row.get("name") for row in popular.get("mid") or []],
        "pro_late_items": [row.get("name") for row in popular.get("late") or []],
    }


def _score_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "hero": row.get("hero"),
        "kills_deaths_assists": f"{row.get('kills')}/{row.get('deaths')}/{row.get('assists')}",
        "net_worth": row.get("net_worth"),
        "gpm": row.get("gpm"),
        "hero_damage": row.get("hero_damage"),
        **({"you": True} if row.get("me") else {}),
    }


def _prune(value: Any) -> Any:
    """Drop None / empty values and round numbers so the prompt stays small and readable."""
    if isinstance(value, dict):
        pruned = {k: _prune(v) for k, v in value.items()}
        return {k: v for k, v in pruned.items() if v not in (None, "", [], {})}
    if isinstance(value, list):
        return [_prune(v) for v in value if v not in (None, "", [], {})]
    if isinstance(value, float):
        # The model copies numbers as given: 590.0 -> 590, 640.33 -> 640, 2.35 -> 2.4.
        # Shares below 1 (0.12 = 12 %) keep their precision.
        if abs(value) < 1:
            return round(value, 3)
        tidy = round(value) if abs(value) >= 100 else round(value, 1)
        return int(tidy) if tidy == int(tidy) else tidy
    return value
