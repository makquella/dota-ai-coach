"""
player_profile.py - the «Профіль» tab: rating graph, app level, achievements
and the «Іскри» the player earns by playing with the coach.

Everything is computed from the match table (and two meta values), so it
rebuilds from a backup and never drifts:

- Rating (FACEIT-like graph): Dota does not give anyone the player's MMR, so
  the player types it in once (`mmr:<account>`, a list of anchors) and every
  ranked match (lobby type 7) with a known result moves it by MMR_STEP. Matches
  before the first anchor are counted backwards from it, so the graph starts
  full. With no MMR typed in, the medal gives a rough start (`source: medal`).
  It is an estimate and the tab says so.
- Level: XP for every match recorded by the app (GSI in `sources`), more for
  a win and for a good review score.
- Achievements: tiered goals over the matches played with the app.
- Sparks («Іскри»): earned per recorded match, per win and per achievement tier;
  spent in the shop (cosmetics.py: the prices of the owned items).
"""

from __future__ import annotations

import json
import re
from collections import Counter
from datetime import UTC, datetime
from typing import Any

from app import cosmetics
from app.analysis_texts import rank_label

RANKED_LOBBY = 7
MMR_STEP = 25  # about what a ranked game moves the MMR
MMR_MIN, MMR_MAX = 0, 15000
MMR_POINTS = 60  # points on the graph
MMR_ANCHORS_MAX = 50
# One star of a medal is about this much MMR (Herald 1 starts at 0, Immortal at 5620).
MMR_PER_STAR = 154
IMMORTAL_MMR = 5620

XP_GAME = 100
XP_WIN = 50
XP_GOOD = 25  # a reviewed match scored GOOD_SCORE or more
GOOD_SCORE = 60
SPARKS_GAME = 10
SPARKS_WIN = 5
TIER_SPARKS = (20, 50, 100, 200, 400, 800)
TIER_NAMES = {
    "uk": ("Бронза", "Срібло", "Золото", "Платина", "Діамант", "Легенда"),
    "en": ("Bronze", "Silver", "Gold", "Platinum", "Diamond", "Legend"),
}

# id, targets per tier, uk/en (title, text with {n} and {w}, the noun's forms:
# one / few / many in Ukrainian, one / other in English).
MATCH_UK = ("матч", "матчі", "матчів")
MATCH_EN = ("match", "matches")
ACHIEVEMENTS: list[dict[str, Any]] = [
    {
        "id": "app_games",
        "targets": (1, 10, 50, 100, 250, 500),
        "uk": ("З тренером", "Зіграйте {n} {w} з Wardly", MATCH_UK),
        "en": ("With the coach", "Play {n} {w} with Wardly", MATCH_EN),
    },
    {
        "id": "app_wins",
        "targets": (1, 10, 50, 100, 250),
        "uk": ("Переможець", "Виграйте {n} {w} з Wardly", MATCH_UK),
        "en": ("Winner", "Win {n} {w} with Wardly", MATCH_EN),
    },
    {
        "id": "win_streak",
        "targets": (3, 5, 7, 10),
        "uk": ("Серія", "Виграйте {n} {w} поспіль з Wardly", MATCH_UK),
        "en": ("Streak", "Win {n} {w} in a row with Wardly", MATCH_EN),
    },
    {
        "id": "good_games",
        "targets": (1, 10, 25, 50, 100),
        "uk": (
            "Чиста гра",
            "Отримайте оцінку розбору 70+ у {n} {w}",
            ("матчі", "матчах", "матчах"),
        ),
        "en": ("Clean game", "Get a review score of 70+ in {n} {w}", MATCH_EN),
    },
    {
        "id": "few_deaths",
        "targets": (1, 5, 15, 30),
        "uk": (
            "Невбиваний",
            "Зіграйте {n} {w} від 20 хвилин, загинувши не більше 2 разів",
            MATCH_UK,
        ),
        "en": ("Unkillable", "Play {n} {w} of 20+ minutes dying twice or less", MATCH_EN),
    },
    {
        "id": "hero_master",
        "targets": (10, 25, 50, 100),
        "uk": ("Майстер героя", "Зіграйте {n} {w} на одному герої з Wardly", MATCH_UK),
        "en": ("Hero master", "Play {n} {w} on one hero with Wardly", MATCH_EN),
    },
    {
        "id": "weeks",
        "targets": (2, 4, 8, 16, 32),
        "uk": (
            "Сталість",
            "Хоча б матч на тиждень з Wardly: {n} {w}",
            ("тиждень", "тижні", "тижнів"),
        ),
        "en": ("Consistency", "At least one match a week with Wardly: {n} {w}", ("week", "weeks")),
    },
    {
        "id": "mmr_gain",
        "targets": (50, 150, 300, 500, 1000),
        "uk": ("Зростання рейтингу", "Підніміть рейтинг на {n} від найнижчої точки графіка", ()),
        "en": ("Climbing", "Raise the rating by {n} from the lowest point of the graph", ()),
    },
]


def plural(n: int, forms: tuple[str, ...], lang: str) -> str:
    """The noun for a number: uk one / few / many, en one / other."""
    if not forms:
        return ""
    if lang != "uk":
        return forms[0] if n == 1 else forms[-1]
    if n % 10 == 1 and n % 100 != 11:
        return forms[0]
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return forms[1]
    return forms[2]


def _int(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value != value:
        return None
    return int(value)


def with_app(row: dict[str, Any]) -> bool:
    """A match the app recorded live (not only fetched from OpenDota)."""
    return "gsi" in (row.get("sources") or [])


# --- rating -------------------------------------------------------------------


def load_anchors(raw: str | None) -> list[dict[str, Any]]:
    try:
        entries = json.loads(raw or "[]")
    except (TypeError, ValueError):
        return []
    anchors = []
    for entry in entries if isinstance(entries, list) else []:
        if not isinstance(entry, dict):
            continue
        at, mmr = _int(entry.get("at")), _int(entry.get("mmr"))
        if at is not None and mmr is not None and MMR_MIN <= mmr <= MMR_MAX:
            anchors.append({"at": at, "mmr": mmr})
    return sorted(anchors, key=lambda a: a["at"])


def add_anchor(raw: str | None, mmr: int, now: float) -> str:
    anchors = load_anchors(raw)
    anchors.append({"at": int(now), "mmr": int(mmr)})
    return json.dumps(anchors[-MMR_ANCHORS_MAX:])


def medal_mmr(rank_tier: Any) -> int | None:
    """A rough MMR in the middle of a medal's star (Immortal: its floor)."""
    tier = _int(rank_tier)
    if tier is None or not 11 <= tier <= 80:
        return None
    medal, stars = divmod(tier, 10)
    if medal >= 8:
        return IMMORTAL_MMR
    if not 1 <= stars <= 5:
        return None
    return ((medal - 1) * 5 + stars - 1) * MMR_PER_STAR + MMR_PER_STAR // 2


def rating(
    rows: list[dict[str, Any]], anchors: list[dict[str, Any]], rank_tier: Any, now: float
) -> dict[str, Any] | None:
    """The rating graph: one point per ranked match with a result, estimated
    from the anchors (the player's own numbers), else from the medal."""
    source = "manual"
    if not anchors:
        start = medal_mmr(rank_tier)
        if start is None:
            return None
        anchors = [{"at": int(now), "mmr": start}]
        source = "medal"
    ranked = sorted(
        (
            r
            for r in rows
            if r.get("lobby_type") == RANKED_LOBBY
            and r.get("win") is not None
            and _int(r.get("start_time"))
        ),
        key=lambda r: (r["start_time"], r.get("match_id") or 0),
    )
    first = anchors[0]
    before = [r for r in ranked if r["start_time"] < first["at"]]
    after = [r for r in ranked if r["start_time"] >= first["at"]]
    points: list[dict[str, Any]] = []
    # Backwards from the first anchor: the value before each earlier match.
    value = first["mmr"]
    back: list[dict[str, Any]] = []
    for row in reversed(before):
        back.append(_point(row, value))
        value -= MMR_STEP if row["win"] else -MMR_STEP
    points.extend(reversed(back))
    # Forwards from each anchor.
    pending = list(anchors)
    value = None
    for row in after:
        while pending and pending[0]["at"] <= row["start_time"]:
            anchor = pending.pop(0)
            value = anchor["mmr"]
            points.append({"t": anchor["at"], "mmr": value, "anchor": True})
        assert value is not None
        value += MMR_STEP if row["win"] else -MMR_STEP
        points.append(_point(row, value))
    for anchor in pending:
        points.append({"t": anchor["at"], "mmr": anchor["mmr"], "anchor": True})
    if source == "medal":
        # The medal guess is only the end of the line, not a typed-in number.
        points = [p for p in points if not p.get("anchor")] or [
            {"t": anchors[0]["at"], "mmr": anchors[0]["mmr"], "anchor": True}
        ]
    shown = points[-MMR_POINTS:]
    games = [p for p in points if "win" in p]
    last20 = games[-20:]
    values = [p["mmr"] for p in shown]
    current = points[-1]["mmr"]
    lowest = min(values)
    return {
        "source": source,
        "current": current,
        "peak": max(values),
        "lowest": lowest,
        "gain_from_lowest": max(0, current - lowest),
        "change_20": current - last20[0]["mmr"] + _delta(last20[0]) if last20 else 0,
        "wins_20": sum(1 for p in last20 if p["win"]),
        "losses_20": sum(1 for p in last20 if not p["win"]),
        "games": len(games),
        "step": MMR_STEP,
        "points": shown,
    }


def _point(row: dict[str, Any], value: int) -> dict[str, Any]:
    return {
        "t": row["start_time"],
        "mmr": value,
        "win": bool(row["win"]),
        "hero_id": row.get("hero_id"),
        "match_id": row.get("match_id"),
    }


def _delta(point: dict[str, Any]) -> int:
    return MMR_STEP if point.get("win") else -MMR_STEP


# --- level, achievements, sparks ---------------------------------------------


def level_of(xp: int) -> dict[str, int]:
    """Level 1 at 0 XP; each next level costs 100 more than the one before (300, 400…)."""
    level, cost, spent = 1, 300, 0
    while xp - spent >= cost:
        spent += cost
        level += 1
        cost += 100
    return {"level": level, "xp": xp, "into": xp - spent, "need": cost}


def _week(ts: int) -> tuple[int, int]:
    iso = datetime.fromtimestamp(ts, UTC).isocalendar()
    return (iso[0], iso[1])


def _metrics(app_rows: list[dict[str, Any]]) -> dict[str, list[tuple[int, int]]]:
    """Per metric: the (start time, value) after each match, oldest first, so a
    tier's date is the match that reached it."""
    series: dict[str, list[tuple[int, int]]] = {a["id"]: [] for a in ACHIEVEMENTS}
    wins = streak = best = good = clean = 0
    heroes: Counter[Any] = Counter()
    weeks: set[tuple[int, int]] = set()
    for games, row in enumerate(app_rows, start=1):
        t = _int(row.get("start_time")) or 0
        if row.get("win"):
            wins += 1
            streak += 1
        elif row.get("win") is False:
            streak = 0
        best = max(best, streak)
        score = _int(row.get("score"))
        if score is not None and score >= 70:
            good += 1
        deaths, duration = _int(row.get("deaths")), _int(row.get("duration")) or 0
        if deaths is not None and deaths <= 2 and duration >= 1200:
            clean += 1
        if row.get("hero_id"):
            heroes[row["hero_id"]] += 1
        if t:
            weeks.add(_week(t))
        for key, value in (
            ("app_games", games),
            ("app_wins", wins),
            ("win_streak", best),
            ("good_games", good),
            ("few_deaths", clean),
            ("hero_master", max(heroes.values(), default=0)),
            ("weeks", len(weeks)),
        ):
            series[key].append((t, value))
    return series


def achievements(
    app_rows: list[dict[str, Any]], mmr_gain: int, lang: str
) -> tuple[list[dict[str, Any]], int]:
    """Every achievement with its reached tier and progress; and the sparks the
    reached tiers give."""
    lang = "uk" if lang == "uk" else "en"
    series = _metrics(app_rows)
    series["mmr_gain"] = [(0, mmr_gain)]
    result, sparks = [], 0
    for spec in ACHIEVEMENTS:
        values = series[spec["id"]]
        value = values[-1][1] if values else 0
        targets = spec["targets"]
        reached = sum(1 for target in targets if value >= target)
        sparks += sum(TIER_SPARKS[i] for i in range(reached))
        unlocked = []
        for index in range(reached):
            at = next((t for t, v in values if v >= targets[index]), 0) or None
            unlocked.append({"tier": index + 1, "at": at})
        title, text, forms = spec[lang]
        target = targets[reached] if reached < len(targets) else targets[-1]
        result.append(
            {
                "id": spec["id"],
                "title": title,
                "text": text.format(n=target, w=plural(target, forms, lang)).replace("  ", " "),
                "tier": reached,
                "tiers": len(targets),
                "tier_name": TIER_NAMES[lang][reached - 1] if reached else None,
                "value": value,
                "target": target,
                "done": reached == len(targets),
                "reward": TIER_SPARKS[reached] if reached < len(targets) else 0,
                "unlocked": unlocked,
            }
        )
    return result, sparks


def build_profile(
    rows: list[dict[str, Any]],
    *,
    player: dict[str, Any] | None,
    mmr_raw: str | None,
    cosmetics_raw: str | None = None,
    lang: str,
    now: float,
) -> dict[str, Any]:
    """The whole tab from the match table (newest first, as the store gives it)."""
    oldest_first = sorted(
        rows, key=lambda r: (_int(r.get("start_time")) or 0, r.get("match_id") or 0)
    )
    app_rows = [r for r in oldest_first if with_app(r)]
    app_wins = sum(1 for r in app_rows if r.get("win"))
    decided = sum(1 for r in app_rows if r.get("win") is not None)
    good = sum(
        1 for r in app_rows if (_int(r.get("score")) or 0) >= GOOD_SCORE and r.get("has_analysis")
    )
    xp = len(app_rows) * XP_GAME + app_wins * XP_WIN + good * XP_GOOD
    rank_tier = (player or {}).get("rank_tier")
    graph = rating(rows, load_anchors(mmr_raw), rank_tier, now)
    badges, tier_sparks = achievements(app_rows, graph["gain_from_lowest"] if graph else 0, lang)
    earned = len(app_rows) * SPARKS_GAME + app_wins * SPARKS_WIN + tier_sparks
    looks = cosmetics.load(cosmetics_raw)
    spent = cosmetics.spent(looks)
    balance = max(0, earned - spent)
    level = level_of(xp)
    tiers = {badge["id"]: badge["tier"] for badge in badges}
    minutes = sum((_int(r.get("duration")) or 0) for r in app_rows) // 60
    return {
        "player": {
            "name": (player or {}).get("persona_name"),
            "avatar_url": (player or {}).get("avatar_url"),
            "rank_tier": rank_tier,
            "rank_label": rank_label(rank_tier, lang),
        },
        "level": level,
        "rating": graph,
        "achievements": badges,
        "sparks": {"balance": balance, "earned": earned, "spent": spent},
        "equipped": cosmetics.equipped(looks, level["level"], tiers),
        "shop": cosmetics.shop(
            looks, balance=balance, level=level["level"], tiers=tiers, lang=lang
        ),
        "stats": {
            "app_games": len(app_rows),
            "app_wins": app_wins,
            "app_winrate": round(100 * app_wins / decided) if decided else None,
            "app_hours": round(minutes / 60, 1),
            "all_games": len(rows),
            "week_games": sum(
                1 for r in app_rows if (_int(r.get("start_time")) or 0) >= now - 7 * 86400
            ),
        },
    }


AVATAR_URL = re.compile(
    r"^https://(?:avatars(?:\.akamai|\.cloudflare|\.fastly)?\.steamstatic\.com"
    r"|steamcdn-a\.akamaihd\.net/steamcommunity/public/images/avatars/[0-9a-f]{2})"
    r"/([0-9a-f]{40})(?:_full|_medium)?\.jpg$"
)


def avatar_hash(url: Any) -> str | None:
    """The Steam avatar's image hash from its CDN address (OpenDota's
    `avatarfull`), the only part of it a public card keeps; None otherwise."""
    match = AVATAR_URL.match(url) if isinstance(url, str) else None
    return match.group(1) if match else None


def public_card(profile: dict[str, Any], lang: str, *, show_mmr: bool = True) -> dict[str, Any]:
    """The part of the profile a player shows friends (services/api/src/profile.js
    validates it again): name, the Steam avatar's image hash, level, medal, the
    rating when typed in, looks, achievement tiers and app stats — never an
    account id or the match list."""
    player = profile.get("player") or {}
    rating_ = profile.get("rating") or {}
    worn = profile.get("equipped") or {}
    title_id = worn.get("title")
    titles = {item["id"]: item["name"] for item in profile.get("shop") or []}
    stats = profile.get("stats") or {}
    manual = rating_.get("source") == "manual"
    return {
        "lang": "en" if lang == "en" else "uk",
        "name": (player.get("name") or "Wardly")[:32],
        "avatar": avatar_hash(player.get("avatar_url")),
        "title": titles.get(title_id) if title_id and title_id != "title_none" else None,
        "level": (profile.get("level") or {}).get("level", 1),
        "rank_tier": player.get("rank_tier"),
        "rank_label": player.get("rank_label"),
        "mmr": rating_.get("current") if show_mmr and manual else None,
        "mmr_change": rating_.get("change_20") if show_mmr and manual else None,
        "equipped": worn,
        "achievements": [
            {"id": b["id"], "tier": b["tier"], "title": b["title"]}
            for b in profile.get("achievements") or []
        ],
        "stats": {
            "app_games": stats.get("app_games", 0),
            "app_winrate": stats.get("app_winrate"),
            "week_games": stats.get("week_games", 0),
        },
    }
