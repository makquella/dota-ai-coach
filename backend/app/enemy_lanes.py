"""
enemy_lanes.py - where the enemy heroes laned and which of them is missing.

The player's GSI minimap shows the enemy heroes the team can see, with their
positions (enemy_heroes.visible_enemy_units). From 1:00 to 6:00 every sighting
counts towards that hero's lane (live_role.lane_of); the lane is the one with
most sightings (LANE_MIN_SAMPLES+). After that, the hero last seen in a lane
and not seen for MISSING_AFTER seconds is «missing» — the old «SS» call:

- the enemy mid, for a player in a side lane (a mid that leaves the lane is
  the most common gank);
- the enemy who stood in the player's own lane (gone to gank another lane, or
  around through the trees).

Only from MISSING_FROM to MISSING_UNTIL (the laning stage), only for heroes seen
within MISSING_RECENT before they went (an enemy never seen says nothing), and
never while the player is dead or in a base.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from app.live_role import lane_of

LANE_FROM, LANE_UNTIL = 60, 6 * 60
LANE_MIN_SAMPLES = 3
SAMPLE_EVERY = 5
MISSING_FROM, MISSING_UNTIL = 2 * 60 + 30, 12 * 60
MISSING_AFTER = 20
MISSING_UNTIL_SECONDS = 60
MISSING_RECENT = 120


class EnemyLanes:
    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self._samples: dict[str, Counter[str]] = {}
        self._last_sample: dict[str, int] = {}
        self._last_seen: dict[str, int] = {}
        self._clock: int | None = None

    def observe(self, clock: Any, units: Any) -> None:
        """One live tick: `units` from visible_enemy_units (None: no minimap)."""
        if not isinstance(clock, int) or not isinstance(units, list):
            return
        if self._clock is not None and clock < self._clock - 30:
            self.reset()  # a new match (or a replay jumped back)
        self._clock = clock
        for unit in units:
            if not isinstance(unit, dict) or not isinstance(unit.get("hero"), str):
                continue
            hero = unit["hero"]
            self._last_seen[hero] = clock
            x, y = unit.get("x"), unit.get("y")
            if not (LANE_FROM <= clock <= LANE_UNTIL) or x is None or y is None:
                continue
            if clock - self._last_sample.get(hero, -SAMPLE_EVERY) < SAMPLE_EVERY:
                continue
            self._last_sample[hero] = clock
            lane = lane_of(float(x), float(y))
            if lane is not None:
                self._samples.setdefault(hero, Counter())[lane] += 1

    def lane(self, hero: str) -> str | None:
        counts = self._samples.get(hero)
        if not counts:
            return None
        lane, n = counts.most_common(1)[0]
        return lane if n >= LANE_MIN_SAMPLES else None

    def lanes(self) -> dict[str, str]:
        return {hero: lane for hero in self._samples if (lane := self.lane(hero))}

    def missing(self, clock: Any, my_lane: str | None) -> dict[str, Any] | None:
        """{hero, lane, kind (mid | lane), since, seconds} for the enemy to call
        missing now, or None. `my_lane`: top / mid / bot where the player is."""
        if not isinstance(clock, int) or not (MISSING_FROM <= clock <= MISSING_UNTIL):
            return None
        if my_lane not in ("top", "mid", "bot"):
            return None
        found = []
        for hero, lane in self.lanes().items():
            if lane == my_lane:
                kind = "lane"
            elif lane == "mid":
                kind = "mid"
            else:
                continue
            seen = self._last_seen.get(hero)
            if seen is None:
                continue
            gone = clock - seen
            if MISSING_AFTER <= gone <= MISSING_UNTIL_SECONDS and seen >= clock - MISSING_RECENT:
                found.append(
                    {"hero": hero, "lane": lane, "kind": kind, "since": seen, "seconds": gone}
                )
        if not found:
            return None
        # The player's own lane opponent first, then the longest gone.
        found.sort(key=lambda row: (row["kind"] != "lane", -row["seconds"]))
        return found[0]
