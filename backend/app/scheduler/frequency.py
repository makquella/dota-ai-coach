"""
scheduler.frequency - the player's "how often" preference for coaching advice.

Only the pauses between regular coaching advice scale: the wall-clock
cooldown, the game-time gaps (coaching, same action, post-laning) and the
long-silence heartbeat nudge. Urgent and safety advice (LOW_HP, death
reviews, recent-damage spacing) never change, whatever the setting.
"""

from __future__ import annotations

# Multiplier on the pauses; None = no heartbeat nudges at all.
FREQUENCIES: dict[str, float] = {"calm": 2.0, "normal": 1.0, "active": 0.6}
DEFAULT_FREQUENCY = "normal"


def normalize_frequency(value: object) -> str:
    text = str(value or "").strip().lower()
    return text if text in FREQUENCIES else DEFAULT_FREQUENCY


def scaled_seconds(seconds: float, frequency: str) -> int:
    return int(round(seconds * FREQUENCIES[normalize_frequency(frequency)]))


def heartbeat_enabled(frequency: str) -> bool:
    """A calm coach does not fill long silences."""
    return normalize_frequency(frequency) != "calm"
