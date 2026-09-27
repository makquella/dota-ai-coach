"""
scheduler.frequency - the player's "how often" preference for coaching advice.

Only the pauses between regular coaching advice scale: the wall-clock
cooldown, the game-time gaps (coaching, same action, post-laning) and the
long-silence heartbeat nudge. Urgent and safety advice (LOW_HP, death
reviews, recent-damage spacing, the UNSCALED_DECISIONS cooldown) never
change, whatever the setting.
"""

from __future__ import annotations

# Safety advice keeps its normal wall-clock cooldown in every mode (LOW_HP,
# disables and death reviews use the urgent cooldown and never scale either).
UNSCALED_DECISIONS = frozenset(
    {
        "LOW_HP_WARNING",
        "RECENT_DAMAGE_WARNING",
        "OVERSTAY_WARNING",
        "HERO_SURVIVABILITY_RISK",
        "ABILITY_SAFETY_COOLDOWN",
        "LOW_MANA",
        "DEAD_WAIT",
        "BUYBACK_AVAILABLE",
        "SMOKED_STATUS",
    }
)

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
