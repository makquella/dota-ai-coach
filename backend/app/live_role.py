"""
live_role.py - the player's position in the current match: carry, mid, offlane
or support.

Timers and role tips (app/map_hints.py) depend on it. In order:
1. the player's choice in the launcher (ROLE_SETTING, "auto" by default);
2. the lane the hero stood in during laning (live GSI coordinates, clock
   1:00-6:00) and the last-hit pace: the safe lane is the carry's unless the
   hero farms like a support, the off lane the offlaner's, mid is mid;
3. before the lane is known: the prior from main.py (the usual position of the
   player's reviews on this hero, else the hero's OpenDota role tags).

Lanes are sampled until 6:00 only, so a support farming a lane later in the
game does not turn into a carry. Only GSI of the player's own hero is used.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from app.advice_context import MAP_CENTER

POSITIONS = ("carry", "mid", "offlane", "support")
SETTINGS = ("auto", *POSITIONS)

LANE_FROM = 60
LANE_UNTIL = 6 * 60
# The lane is read once this much laning has been seen (3:00 clock, 20 samples).
LANE_DECIDE_AT = 3 * 60
MIN_LANE_SAMPLES = 20
SAMPLE_EVERY = 5
# Last hits per minute that make a lane hero a farmer (carry / offlaner).
CARRY_LH_PER_MIN = 2.0
OFFLANE_LH_PER_MIN = 1.5
# Map geometry (centred world units): the mid lane runs along x == y.
MID_BAND = 2200
BASE_EDGE = 5500
MAX_BACKWARD_SECONDS = 30

_setting = "auto"


def set_role_setting(value: str) -> str:
    global _setting
    _setting = value if value in SETTINGS else "auto"
    return _setting


def role_setting() -> str:
    return _setting


def lane_of(x: float, y: float) -> str | None:
    """ "top", "mid" or "bot" for absolute replay coordinates; None in a base."""
    u, v = x - MAP_CENTER, y - MAP_CENTER
    if abs(u) > BASE_EDGE and abs(v) > BASE_EDGE and (u > 0) == (v > 0):
        return None  # fountain / base corner
    d = v - u
    if abs(d) < MID_BAND:
        return "mid"
    return "top" if d > 0 else "bot"


def lane_kind(lane: str, team: str | None) -> str | None:
    """safe / off / mid for the player's team (Radiant's safe lane is bottom)."""
    if lane == "mid":
        return "mid"
    if team not in {"radiant", "dire"}:
        return None
    safe = "bot" if team == "radiant" else "top"
    return "safe" if lane == safe else "off"


class LiveRoleTracker:
    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self._lanes: Counter[str] = Counter()
        self._next_sample: int | None = None
        self._clock: int | None = None
        self._last_hits: int | None = None
        self._team: str | None = None
        self._current: dict[str, Any] | None = None

    def observe(
        self,
        clock: int | None,
        *,
        x: float | None,
        y: float | None,
        last_hits: int | None,
        team: str | None,
        alive: bool | None,
    ) -> None:
        if clock is None:
            return
        if self._clock is not None and clock < self._clock - MAX_BACKWARD_SECONDS:
            self.reset()
        self._clock = int(clock)
        if team:
            self._team = str(team).lower()
        if last_hits is not None:
            self._last_hits = int(last_hits)
        # Lanes are sampled until 6:00 only, so the read then stays.
        if not (LANE_FROM <= clock <= LANE_UNTIL):
            return
        if alive is False or x is None or y is None:
            return
        if self._next_sample is not None and clock < self._next_sample:
            return
        self._next_sample = int(clock) + SAMPLE_EVERY
        lane = lane_of(float(x), float(y))
        if lane is not None:
            self._lanes[lane] += 1
        self._decide()

    def _decide(self) -> None:
        clock = self._clock or 0
        if clock < LANE_DECIDE_AT or sum(self._lanes.values()) < MIN_LANE_SAMPLES:
            return
        lane, _count = self._lanes.most_common(1)[0]
        kind = lane_kind(lane, self._team)
        if kind is None:
            return
        pace = (self._last_hits or 0) / max(1.0, clock / 60)
        if kind == "mid":
            role = "mid"
        elif kind == "safe":
            role = "carry" if pace >= CARRY_LH_PER_MIN else "support"
        else:
            role = "offlane" if pace >= OFFLANE_LH_PER_MIN else "support"
        self._current = {"role": role, "source": "lane", "lane": kind}

    def role(self, prior: dict[str, Any] | None = None) -> dict[str, Any] | None:
        """{"role", "source": setting|lane|history|hero, "lane"?} or None (unknown)."""
        if _setting != "auto":
            return {"role": _setting, "source": "setting"}
        if self._current is not None:
            return dict(self._current)
        if prior and prior.get("role") in POSITIONS:
            return dict(prior)
        return None
