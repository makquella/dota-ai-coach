"""
career_deaths.py - where the player dies over the last MATCHES matches (Progress).

From the stored reviews' map blocks (`analysis.map.deaths`, map_analysis.py):
every death with a known team side, turned so the player is always Radiant —
a Dire game is rotated half a turn around the map centre, which is how the map
itself is built, so «your safe lane», «your jungle» and «the enemy jungle» land
on the same spot whichever side the game was on. Then the places where deaths
keep repeating (the same zone and half, SPOT_MIN+ deaths from 2+ matches, the
labels of map_analysis zones on this turned map), deaths per half, and the share
of deaths after the laning stage on the enemy half. Facts only.
"""

from __future__ import annotations

from typing import Any

from app.advice_context import MAP_CENTER
from app.analysis_texts import place_label
from app.map_analysis import LANING_END_SECONDS, MAP_MAX, MAP_MIN, zone

MATCHES = 20
MIN_DEATHS = 5
SPOT_MIN = 3
SPOT_MATCHES = 2
MAX_SPOTS = 3
SIDES = ("own", "river", "enemy")


def _as_radiant(x: float, y: float, is_radiant: bool) -> tuple[int, int]:
    if is_radiant:
        return round(x), round(y)
    return round(2 * MAP_CENTER - x), round(2 * MAP_CENTER - y)


def death_map(matches: list[dict[str, Any]], lang: str) -> dict[str, Any] | None:
    """`matches`: newest first with their analysis. None under MIN_DEATHS deaths."""
    games = []
    for match in matches:
        block = (match.get("analysis") or {}).get("map") or {}
        if block.get("is_radiant") is None or not block.get("deaths"):
            continue
        games.append((match, block))
        if len(games) >= MATCHES:
            break
    deaths: list[dict[str, Any]] = []
    for match, block in games:
        for death in block["deaths"]:
            if death.get("side") not in SIDES or death.get("t") is None:
                continue
            x, y = _as_radiant(death["x"], death["y"], bool(block["is_radiant"]))
            entry = {
                "t": death["t"],
                "x": x,
                "y": y,
                "side": death["side"],
                "match_id": match["match_id"],
                "hero": match.get("hero"),
                "hero_id": match.get("hero_id"),
            }
            if death.get("killer"):
                entry["killer"] = death["killer"]
            deaths.append(entry)
    if len(deaths) < MIN_DEATHS:
        return None
    groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for death in deaths:
        groups.setdefault((zone(death["x"], death["y"]), death["side"]), []).append(death)
    spots = []
    for (zone_id, side), group in groups.items():
        matches_there = len({d["match_id"] for d in group})
        if len(group) < SPOT_MIN or matches_there < SPOT_MATCHES:
            continue
        spots.append(
            {
                "zone": zone_id,
                "side": side,
                "label": place_label(zone_id, side, lang),
                "count": len(group),
                "matches": matches_there,
                "x": round(sum(d["x"] for d in group) / len(group)),
                "y": round(sum(d["y"] for d in group) / len(group)),
            }
        )
    spots.sort(key=lambda spot: (-spot["count"], -spot["matches"]))
    later = [d for d in deaths if d["t"] >= LANING_END_SECONDS]
    return {
        "matches": len(games),
        "total": len(deaths),
        "per_match": round(len(deaths) / len(games), 1),
        "deaths": deaths,
        "by_side": {side: sum(1 for d in deaths if d["side"] == side) for side in SIDES},
        "enemy_share_late": (
            round(100 * sum(1 for d in later if d["side"] == "enemy") / len(later))
            if later
            else None
        ),
        "spots": spots[:MAX_SPOTS],
        "bounds": [MAP_MIN, MAP_MAX],
    }
