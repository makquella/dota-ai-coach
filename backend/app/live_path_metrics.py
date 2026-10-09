"""Bounded local timing observations; no packets, identifiers or advice text."""

from __future__ import annotations

import math
import threading
from collections import deque
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from time import perf_counter
from typing import Literal

Phase = Literal["gsi.total", "gsi.prepare", "gsi.policy", "gsi.persistence", "demo.total"]
PHASES: tuple[Phase, ...] = (
    "gsi.total",
    "gsi.prepare",
    "gsi.policy",
    "gsi.persistence",
    "demo.total",
)
MAX_SAMPLES = 256


@dataclass
class _Timing:
    samples: deque[float] = field(default_factory=lambda: deque(maxlen=MAX_SAMPLES))
    count: int = 0
    failed: int = 0
    running: int = 0
    last_at: str | None = None


class LivePathMetrics:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._timings = {phase: _Timing() for phase in PHASES}

    @contextmanager
    def measure(self, phase: Phase) -> Iterator[None]:
        started = perf_counter()
        failed = False
        with self._lock:
            self._timings[phase].running += 1
        try:
            yield
        except BaseException:
            failed = True
            raise
        finally:
            elapsed = max(0.0, (perf_counter() - started) * 1000)
            at = datetime.now(UTC).isoformat(timespec="milliseconds")
            with self._lock:
                timing = self._timings[phase]
                timing.running -= 1
                timing.count += 1
                timing.failed += int(failed)
                timing.samples.append(elapsed)
                timing.last_at = at

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            captured = [
                (phase, list(t.samples), t.count, t.failed, t.running, t.last_at)
                for phase, t in self._timings.items()
            ]
        result: dict[str, object] = {}
        for phase, samples, count, failed, running, at in captured:
            ordered = sorted(samples)
            result[phase] = {
                "count": count,
                "failed": failed,
                "running": running,
                "sample_count": len(samples),
                "latest_ms": round(samples[-1], 3) if samples else None,
                "p50_ms": self._percentile(ordered, 0.5),
                "p95_ms": self._percentile(ordered, 0.95),
                "last_at": at,
            }
        return {"unit": "ms", "max_samples_per_phase": MAX_SAMPLES, "phases": result}

    @staticmethod
    def _percentile(samples: list[float], fraction: float) -> float | None:
        if not samples:
            return None
        return round(samples[max(0, math.ceil(len(samples) * fraction) - 1)], 3)


LIVE_PATH_METRICS = LivePathMetrics()
