"""
death_review.py - every death of the match with what the app knows around it.

For each death (facts.deaths_log, merged from OpenDota and the GSI timeline):
- where: the map side (own / river / enemy half, map_analysis.map_side) and the
  zone (a lane, the jungle, a base) when a position is known (GSI: the last
  alive position; a parsed replay: team fight deaths);
- who killed the hero (OpenDota kill logs);
- unspent gold at the moment of death (GSI only);
- the advice shown in the WARNING_WINDOW seconds before it (the live advice log);
- a death soon after respawning from the previous one;
- the last seconds before it (GSI, last_moments.py): the HP curve, a burst kill
  (`burst`), and saving items that were ready while the hero could still act
  (`saver_ready`: ready on a second of the last 5 s without a stun, hex or
  mute — `usable`, the same sample).

Only facts, no guesses: a missing value stays out. The launcher renders the
zone and note ids in the review language («Смерти» card).
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from typing import Any

from app.map_analysis import map_side, zone

WARNING_WINDOW = 30
UNSPENT_GOLD = 1000
SOON_AFTER_RESPAWN = 60
LANING_END = 10 * 60


def review_deaths(facts: Mapping[str, Any]) -> dict[str, Any] | None:
    """{"deaths": [...], "notes": {note id: count}} or None without deaths."""
    deaths = sorted(
        (d for d in facts.get("deaths_log") or [] if d.get("t") is not None),
        key=lambda d: d["t"],
    )
    if not deaths:
        return None
    is_radiant = facts.get("is_radiant")
    advice = sorted(
        (a for a in facts.get("advice_log") or [] if a.get("t") is not None),
        key=lambda a: a["t"],
    )
    rows = []
    previous: dict[str, Any] | None = None
    for death in deaths:
        t = int(death["t"])
        row: dict[str, Any] = {"t": t, "phase": "laning" if t < LANING_END else "late"}
        notes: list[str] = []
        if death.get("killer"):
            row["killer"] = death["killer"]
        x, y = death.get("x"), death.get("y")
        if isinstance(x, (int, float)) and isinstance(y, (int, float)):
            row["zone"] = zone(x, y)
            if is_radiant is not None:
                row["side"] = map_side(x, y, bool(is_radiant))
                if row["side"] == "enemy":
                    notes.append("enemy_half")
        gold = death.get("gold")
        if isinstance(gold, int):
            row["gold"] = gold
            if gold >= UNSPENT_GOLD:
                notes.append("unspent_gold")
        warning = next(
            (a for a in reversed(advice) if t - WARNING_WINDOW <= a["t"] < t),
            None,
        )
        if warning is not None:
            row["warning"] = {
                "t": int(warning["t"]),
                "action": warning.get("action"),
                "mode": warning.get("mode"),
            }
            notes.append("warned")
        if previous is not None and previous.get("respawn"):
            back = int(previous["t"]) + int(previous["respawn"])
            if 0 <= t - back <= SOON_AFTER_RESPAWN:
                row["after_respawn"] = t - back
                notes.append("soon_after_respawn")
        last = death.get("last")
        if isinstance(last, dict) and last.get("hp"):
            row["last"] = {
                "hp": last["hp"],
                "ready": list(last.get("ready") or []),
                "usable": list(last.get("usable") or []),
                "free_s": last.get("free_s", 0),
            }
            if last.get("burst_s"):
                row["last"]["burst_s"] = last["burst_s"]
                notes.append("burst")
            if last.get("usable"):
                notes.append("saver_ready")
        row["notes"] = notes
        rows.append(row)
        previous = death
    counts = Counter(note for row in rows for note in row["notes"])
    return {
        "deaths": rows,
        "notes": dict(counts),
        "window": WARNING_WINDOW,
        # How many deaths have their last seconds (live GSI only).
        "with_last": sum(1 for row in rows if "last" in row),
    }
