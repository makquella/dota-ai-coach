"""
map_analysis.py - where things happened: deaths, wards, the hero's path, laning position.

Coordinates are absolute replay units (centre MAP_CENTER, the playable map is
about 8000..24600 on both axes); see match_facts.py. Radiant's base is the
bottom-left corner (small x and y), Dire's the top-right one, and the river
runs along the other diagonal, so "the enemy half" is decided by x + y.

One rule comes out of it: after laning, most deaths on the enemy half of the
map mean the hero farmed or walked there without knowing where enemies were.
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


def _point(entry: dict[str, Any]) -> tuple[int, int] | None:
    x, y = entry.get("x"), entry.get("y")
    if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
        return None
    if not (MAP_MIN <= x <= MAP_MAX and MAP_MIN <= y <= MAP_MAX):
        return None
    return round(x), round(y)


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
    later = [d for d in deaths if d["t"] >= LANING_END_SECONDS and "side" in d]
    enemy = [d for d in later if d["side"] == "enemy"]
    if len(later) >= MIN_DEATHS_FOR_RULE and len(enemy) / len(later) >= ENEMY_HALF_SHARE:
        findings.append(
            {
                "id": "deaths_enemy_half",
                "kind": "improve",
                "section": "survival",
                "severity": 2,
                "weight": float(len(enemy)),
                "params": {"count": len(enemy), "total": len(later)},
            }
        )
    block = {
        "is_radiant": is_radiant,
        "deaths": deaths,
        "wards": wards,
        "path": _thin(path, MAX_PATH_POINTS),
        "lane": lane,
        "bounds": [MAP_MIN, MAP_MAX],
        "deaths_by_side": {
            side: sum(1 for d in deaths if d.get("side") == side)
            for side in ("own", "river", "enemy")
        },
    }
    return block, findings
