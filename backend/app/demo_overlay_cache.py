"""Short-lived detached demo responses with reset-safe publication."""

from __future__ import annotations

import threading
from collections.abc import Iterator
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import dataclass


@dataclass(frozen=True)
class DemoToken:
    generation: int
    sequence: int


@dataclass(frozen=True)
class _Frame:
    response: dict[str, object]
    expires_at: float


class DemoOverlayCache:
    """Only response/token publication is owned here, not demo processing."""

    def __init__(self, *, ttl_seconds: float = 8) -> None:
        self._lock = threading.Lock()
        self._ttl = ttl_seconds
        self._generation = 0
        self._sequence = 0
        self._last_published = 0
        self._reset_depth = 0
        self._frame: _Frame | None = None

    def reserve(self) -> DemoToken:
        with self._lock:
            self._sequence += 1
            return DemoToken(self._generation, self._sequence)

    def publish(self, response: dict[str, object], token: DemoToken, *, now: float) -> bool:
        # A slow copy cannot block reset or publication of a newer response.
        private = deepcopy(response)
        with self._lock:
            if self._reset_depth or token.generation != self._generation:
                return False
            if token.sequence <= self._last_published:
                return False
            self._frame = _Frame(private, now + self._ttl)
            self._last_published = token.sequence
            return True

    def capture(self, *, now: float) -> dict[str, object] | None:
        with self._lock:
            frame = self._frame
            if frame is not None and now > frame.expires_at:
                self._frame = None
                frame = None
        # Published values are private and never mutated; readers own their copy.
        return deepcopy(frame.response) if frame is not None else None

    def clear(self) -> None:
        with self._lock:
            self._invalidate_locked()

    @contextmanager
    def resetting(self) -> Iterator[None]:
        # Invalidate both before and after reset; reject tokens reserved during
        # the window too. Overlapping resets keep publication disabled until all
        # have finished. Never hold the cache lock while resetting other owners.
        with self._lock:
            self._reset_depth += 1
            self._invalidate_locked()
        try:
            yield
        finally:
            with self._lock:
                self._reset_depth -= 1
                self._invalidate_locked()

    def _invalidate_locked(self) -> None:
        self._generation += 1
        self._frame = None
