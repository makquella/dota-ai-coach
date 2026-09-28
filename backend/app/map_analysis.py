"""
map_analysis.py - where things happened: deaths, wards, the hero's path, laning position.

Coordinates are absolute replay units (centre MAP_CENTER, the playable map is
about 8000..24600 on both axes); see match_facts.py. Radiant's base is the
bottom-left corner (small x and y), Dire's the top-right one, and the river
runs along the other diagonal, so "the enemy half" is decided by x + y.

Two rules come out of it: after laning, most deaths on the enemy half of the
map mean the hero farmed or walked there without knowing where enemies were;
and deaths that keep happening in one place (the same zone and half, `spots`)
get a route drill for that place (`deaths_same_place`; on the enemy half the
first rule names the place instead).
The block itself is drawn by the launcher (schematic map, no game art).
"""

from __future__ import annotations

from typing import Any

from app.advice_context import MAP_CENTER

MAP_MIN = 7000
MAP_MAX = 25800
# Deaths in the river band (either side) count for neither half.
RIVER_BAND = 1400
LANING_END_SECONDS = 10 * 60
MIN_DEATHS_FOR_RULE = 3
ENEMY_HALF_SHARE = 0.6
MAX_PATH_POINTS = 400
MAX_LANE_POINTS = 120
# Deaths in one zone and half of the map: a spot on the map from 2, a finding
# (with a route drill) from 3.
MIN_SPOT_DEATHS = 2
MIN_SPOT_FINDING = 3

# Centred world units: lanes run along the map edges (about ±6400), mid along
# x == y, bases fill the corners; everything else is jungle.
EDGE_LANE = 5000
MID_BAND = 900  # |x - y|: about 640 units either side of the mid lane
BASE_EDGE = 5000


def zone(x: float, y: float) -> str:
    """top / mid / bot lane, base or jungle for absolute replay coordinates."""
    u, v = x - MAP_CENTER, y - MAP_CENTER
    if abs(u) > BASE_EDGE and abs(v) > BASE_EDGE and (u > 0) == (v > 0):
        return "base"
    if u < -EDGE_LANE or v > EDGE_LANE:
        return "top"
    if v < -EDGE_LANE or u > EDGE_LANE:
        return "bot"
    if abs(u - v) < MID_BAND:
        return "mid"
    return "jungle"


def _point(entry: dict[str, Any]) -> tuple[int, int] | None:
    x, y = entry.get("x"), entry.get("y")
    if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
        return None
    if not (MAP_MIN <= x <= MAP_MAX and MAP_MIN <= y <= MAP_MAX):
        return None
    return round(x), round(y)


def death_spots(deaths: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Places with MIN_SPOT_DEATHS+ deaths: the same zone and half of the map,
    most deaths first — {zone, side, count, times, x, y (their middle)}."""
    groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for death in deaths:
        if "side" in death:
            groups.setdefault((zone(death["x"], death["y"]), death["side"]), []).append(death)
    spots = [
        {
            "zone": where[0],
            "side": where[1],
            "count": len(group),
            "times": [d["t"] for d in group],
            "x": round(sum(d["x"] for d in group) / len(group)),
            "y": round(sum(d["y"] for d in group) / len(group)),
        }
        for where, group in groups.items()
        if len(group) >= MIN_SPOT_DEATHS
    ]
    return sorted(spots, key=lambda spot: (-spot["count"], spot["times"][0]))


def map_side(x: float, y: float, is_radiant: bool) -> str:
    """ "own", "enemy" or "river" half for the player's team."""
    towards_dire = (x - MAP_CENTER) + (y - MAP_CENTER)
    if abs(towards_dire) <= RIVER_BAND:
        return "river"
    dire_half = towards_dire > 0
    return "enemy" if dire_half == is_radiant else "own"


def _thin(points: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    if len(points) <= limit:
        return points
    step = len(points) / limit
    return [points[int(i * step)] for i in range(limit)]


def analyze_map(facts: dict[str, Any]) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    """(block for the review or None, findings)."""
    is_radiant = facts.get("is_radiant")
    deaths = []
    for death in facts.get("deaths_log") or []:
        point = _point(death)
        if point is None or death.get("t") is None:
            continue
        entry = {"t": death["t"], "x": point[0], "y": point[1]}
        if death.get("killer"):
            entry["killer"] = death["killer"]
        if is_radiant is not None:
            entry["side"] = map_side(point[0], point[1], bool(is_radiant))
        deaths.append(entry)
    wards = []
    for ward in facts.get("wards") or []:
        point = _point(ward)
        if point is not None:
            wards.append({"t": ward.get("t"), "x": point[0], "y": point[1], "kind": ward["kind"]})
    path = []
    for sample in facts.get("path") or []:
        point = _point(sample)
        if point is not None:
            path.append({"t": sample.get("t"), "x": point[0], "y": point[1]})
    lane = sorted(
        (
            [x, y, n]
            for x, y, n in facts.get("lane_pos") or []
            if _point({"x": x, "y": y}) is not None
        ),
        key=lambda item: -item[2],
    )[:MAX_LANE_POINTS]
    if not (deaths or wards or path or lane):
        return None, []

    findings: list[dict[str, Any]] = []
    spots = death_spots(deaths)
    later = [d for d in deaths if d["t"] >= LANING_END_SECONDS and "side" in d]
    enemy = [d for d in later if d["side"] == "enemy"]
    if len(later) >= MIN_DEATHS_FOR_RULE and len(enemy) / len(later) >= ENEMY_HALF_SHARE:
        params: dict[str, Any] = {"count": len(enemy), "total": len(later)}
        enemy_spot = next((spot for spot in spots if spot["side"] == "enemy"), None)
        if enemy_spot:
            params["spot_zone"] = enemy_spot["zone"]
        findings.append(
            {
                "id": "deaths_enemy_half",
                "kind": "improve",
                "section": "survival",
                "severity": 2,
                "weight": float(len(enemy)),
                "params": params,
            }
        )
    own_spot = next(
        (s for s in spots if s["side"] != "enemy" and s["count"] >= MIN_SPOT_FINDING), None
    )
    if own_spot:
        findings.append(
            {
                "id": "deaths_same_place",
                "kind": "improve",
                "section": "survival",
                "severity": 2,
                "weight": float(own_spot["count"]),
                "params": {
                    "zone": own_spot["zone"],
                    "side": own_spot["side"],
                    "count": own_spot["count"],
                    "of": sum(1 for d in deaths if "side" in d),
                    "times": own_spot["times"],
                },
            }
        )
    block = {
        "is_radiant": is_radiant,
        "deaths": deaths,
        "wards": wards,
        "path": _thin(path, MAX_PATH_POINTS),
        "lane": lane,
        "bounds": [MAP_MIN, MAP_MAX],
        "spots": spots,
        "deaths_by_side": {
            side: sum(1 for d in deaths if d.get("side") == side)
            for side in ("own", "river", "enemy")
        },
    }
    return block, findings
