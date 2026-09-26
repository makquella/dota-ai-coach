"""
farm_tracker.py - "no farm lately" signal for live advice.

GSI gives the running last-hit count and the game clock. MatchMemory feeds
one sample every few seconds of game time; `stall()` reports when a hero who
normally farms took almost no last hits over the last minutes while alive
(dead time does not count as a stall). Conservative on purpose: no signal
without enough history, before minute 12, or for heroes that do not farm
(supports).
"""

from __future__ import annotations

from collections import deque
from itertools import pairwise
from typing import Any

SAMPLE_EVERY_SECONDS = 5
STALL_WINDOW_SECONDS = 240
STALL_MAX_LAST_HITS = 3
STALL_MIN_CLOCK_SECONDS = 12 * 60
# Last hits per minute before the window: below this the hero is not farming
# by design (support) and no stall advice is given.
MIN_FARMING_RATE = 2.5
MIN_ALIVE_SHARE = 0.75
# A missing stretch longer than this (reconnect, replay seek) breaks the window.
MAX_SAMPLE_GAP_SECONDS = 30


class FarmTracker:
    def __init__(self) -> None:
        self.samples: deque[tuple[int, int, bool]] = deque(maxlen=200)

    def reset(self) -> None:
        self.samples.clear()

    def observe(
        self, clock: int | None, last_hits: int | None, alive: bool | None, paused: bool = False
    ) -> None:
        if clock is None or last_hits is None or paused:
            return
        if self.samples:
            last_clock = self.samples[-1][0]
            if clock < last_clock - MAX_SAMPLE_GAP_SECONDS or last_hits < self.samples[-1][1]:
                self.samples.clear()  # rewound or a different match
            elif clock - last_clock < SAMPLE_EVERY_SECONDS:
                return
        self.samples.append((int(clock), int(last_hits), alive is not False))

    def stall(self) -> dict[str, Any] | None:
        if len(self.samples) < 3:
            return None
        now_clock, now_lh, _ = self.samples[-1]
        if now_clock < STALL_MIN_CLOCK_SECONDS:
            return None
        start = now_clock - STALL_WINDOW_SECONDS
        window = [s for s in self.samples if s[0] >= start]
        before = [s for s in self.samples if s[0] <= start]
        if not before or not window:
            return None  # not enough history yet
        base_clock, base_lh, _ = before[-1]
        stretch = [before[-1], *window]
        if any(b[0] - a[0] > MAX_SAMPLE_GAP_SECONDS for a, b in pairwise(stretch)):
            return None
        gained = now_lh - base_lh
        alive_share = sum(1 for s in window if s[2]) / len(window)
        rate_before = base_lh / max(1.0, base_clock / 60)
        if (
            gained > STALL_MAX_LAST_HITS
            or alive_share < MIN_ALIVE_SHARE
            or rate_before < MIN_FARMING_RATE
        ):
            return None
        return {
            "minutes": round((now_clock - base_clock) / 60),
            "last_hits": gained,
            "since_clock": base_clock,
        }
