"""
session_summary.py - «Итог вечера»: the games of one sitting, and a text to share.

From the stored match table and reviews (no network), like weekly_summary: the
newest matches chained by starts at most SESSION_CHAIN_GAP apart, the last of
them over less than SESSION_RECENT ago, and at least SESSION_MIN_GAMES games.
It gives the games, wins and losses, the time played, the average score against
the player's usual one (up to USUAL_MATCHES scored matches before the sitting,
USUAL_MIN needed), the heroes with their records, the best match, the average
deaths, the mistake that came back in 2+ games of the sitting, the focus
results, and `text`: the same in a few plain lines in the request language, with
the site link (`?ref=session`), for the player to paste in a chat. Nothing in it
names the player, the match ids or other players.

`id` changes with every new game of the sitting, so the launcher shows the card
again after one more match.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from app.analysis_texts import render_finding
from app.focus_goal import focus_summary
from app.weekly_summary import NOT_A_HABIT

SESSION_CHAIN_GAP = 3 * 3600  # between the starts of two games of one sitting
SESSION_RECENT = 12 * 3600  # since the end of its last game
SESSION_MIN_GAMES = 2
USUAL_MATCHES = 20
USUAL_MIN = 5
MIN_REPEATS = 2
SITE = "https://luhovyimvp.dev/"


def _score(match: dict[str, Any]) -> float | None:
    value = match.get("score")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def sitting(matches: list[dict[str, Any]], now: float) -> list[dict[str, Any]]:
    """The games of the newest sitting, newest first ([] when it is too old)."""
    started = [m for m in matches if isinstance(m.get("start_time"), int)]
    started = [m for m in started if m["start_time"] <= now]
    if not started:
        return []
    newest = started[0]
    if now - (newest["start_time"] + (newest.get("duration") or 0)) > SESSION_RECENT:
        return []
    games = [newest]
    for match in started[1:]:
        if games[-1]["start_time"] - match["start_time"] > SESSION_CHAIN_GAP:
            break
        games.append(match)
    return games


def _plural_ru(n: int, one: str, few: str, many: str) -> str:
    if n % 10 == 1 and n % 100 != 11:
        return one
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return few
    return many


def _duration_text(minutes: int, ru: bool) -> str:
    hours, rest = divmod(minutes, 60)
    if ru:
        return f"{hours} ч {rest:02d} мин" if hours else f"{rest} мин"
    return f"{hours} h {rest:02d} min" if hours else f"{rest} min"


def share_text(summary: dict[str, Any], lang: str) -> str:
    """A few plain lines for a chat; the numbers are the summary's own."""
    ru = lang == "ru"
    games, wins, losses = summary["games"], summary["wins"], summary["losses"]
    if ru:
        lines = [
            "Итог вечера в Dota 2 · Wardly",
            f"{games} {_plural_ru(games, 'матч', 'матча', 'матчей')}: "
            f"{wins} {_plural_ru(wins, 'победа', 'победы', 'побед')}, "
            f"{losses} {_plural_ru(losses, 'поражение', 'поражения', 'поражений')}"
            f" · {_duration_text(summary['minutes'], True)}",
        ]
    else:
        lines = [
            "My Dota 2 evening · Wardly",
            f"{games} matches: {wins} {'win' if wins == 1 else 'wins'}, "
            f"{losses} {'loss' if losses == 1 else 'losses'}"
            f" · {_duration_text(summary['minutes'], False)}",
        ]
    if summary.get("avg_score") is not None:
        usual = summary.get("usual_score")
        if ru:
            tail = f" (обычно {usual})" if usual is not None else ""
            lines.append(f"Средняя оценка тренера: {summary['avg_score']}/100{tail}")
        else:
            tail = f" (usually {usual})" if usual is not None else ""
            lines.append(f"Average coach score: {summary['avg_score']}/100{tail}")
    heroes = ", ".join(
        f"{h['hero']} {h['wins']}–{h['games'] - h['wins']}" for h in summary["heroes"]
    )
    if heroes:
        lines.append(f"{'Герои' if ru else 'Heroes'}: {heroes}")
    best = summary.get("best")
    if best:
        label = "Лучший матч" if ru else "Best match"
        lines.append(f"{label}: {best['hero'] or '—'}, {best['score']}/100")
    problem = summary.get("top_problem")
    if problem:
        if ru:
            lines.append(
                f"Над чем работать: {problem['title']} ({problem['count']} из {problem['of']})"
            )
        else:
            lines.append(f"To work on: {problem['title']} ({problem['count']} of {problem['of']})")
    focus = summary.get("focus")
    if focus:
        if ru:
            lines.append(f"Фокус «{focus['title']}»: {focus['met']} из {focus['total']}")
        else:
            lines.append(f"Focus «{focus['title']}»: {focus['met']} of {focus['total']}")
    lines.append(f"{SITE}{'' if ru else 'en/'}?ref=session")
    return "\n".join(lines)


def session_summary(
    matches: list[dict[str, Any]],
    now: float,
    lang: str,
    focus: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """`matches`: newest first with their analysis (PlayerStore.matches_for_career).
    None without a recent sitting of SESSION_MIN_GAMES+ games."""
    games = sitting(matches, now)
    if len(games) < SESSION_MIN_GAMES:
        return None
    first, last = games[-1], games[0]
    decided = [m for m in games if m.get("win") is not None]
    wins = sum(1 for m in decided if m["win"])
    scores = [s for s in (_score(m) for m in games) if s is not None]
    earlier = [m for m in matches if (m.get("start_time") or 0) < first["start_time"]]
    usual = [s for s in (_score(m) for m in earlier) if s is not None][:USUAL_MATCHES]
    deaths = [m["deaths"] for m in games if isinstance(m.get("deaths"), int)]
    ended = last["start_time"] + (last.get("duration") or 0)
    summary: dict[str, Any] = {
        "id": f"{first['start_time']}:{last['match_id']}",
        "games": len(games),
        "wins": wins,
        "losses": len(decided) - wins,
        "started": first["start_time"],
        "ended": ended,
        "minutes": max(0, round((ended - first["start_time"]) / 60)),
        "avg_score": round(sum(scores) / len(scores)) if scores else None,
        "usual_score": round(sum(usual) / len(usual)) if len(usual) >= USUAL_MIN else None,
        "avg_deaths": round(sum(deaths) / len(deaths), 1) if deaths else None,
    }
    if summary["avg_score"] is not None and summary["usual_score"] is not None:
        summary["score_change"] = summary["avg_score"] - summary["usual_score"]
    heroes: dict[str, dict[str, Any]] = {}
    for match in reversed(games):  # in the order played
        if not match.get("hero"):
            continue
        row = heroes.setdefault(
            match["hero"],
            {"hero": match["hero"], "hero_id": match.get("hero_id"), "games": 0, "wins": 0},
        )
        row["games"] += 1
        row["wins"] += 1 if match.get("win") else 0
    summary["heroes"] = sorted(heroes.values(), key=lambda h: -h["games"])
    scored = [m for m in games if _score(m) is not None]
    if scored:
        best = max(scored, key=lambda m: (m["score"], m.get("start_time") or 0))
        summary["best"] = {
            "match_id": best["match_id"],
            "hero": best.get("hero"),
            "hero_id": best.get("hero_id"),
            "score": best["score"],
            "win": best.get("win"),
        }
    counts: Counter[str] = Counter()
    latest: dict[str, dict[str, Any]] = {}
    for match in games:  # newest first: `latest` keeps the newest wording
        findings = (match.get("analysis") or {}).get("improvements") or []
        for finding in {f["id"]: f for f in reversed(findings)}.values():
            if finding["id"] in NOT_A_HABIT:
                continue
            counts[finding["id"]] += 1
            latest.setdefault(finding["id"], finding)
    repeated = [(fid, n) for fid, n in counts.most_common() if n >= MIN_REPEATS]
    if repeated:
        finding_id, count = repeated[0]
        summary["top_problem"] = {
            "id": finding_id,
            "title": render_finding(latest[finding_id], lang).get("title"),
            "count": count,
            "of": len(games),
        }
    if focus is not None:
        plan = focus_summary(focus, games, lang)
        if plan["results"]:
            summary["focus"] = {
                "id": plan["id"],
                "title": plan["title"],
                "met": sum(1 for r in plan["results"] if r["met"]),
                "total": len(plan["results"]),
            }
    summary["text"] = share_text(summary, lang)
    return summary
