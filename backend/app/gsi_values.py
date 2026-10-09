"""Pure scalar conversions shared by GSI and ability normalization."""

from __future__ import annotations

import math
from typing import Any

# No real GSI number (gold, experience, clock, coordinates, cooldowns) comes
# near this; anything larger, and inf/nan, is garbage and counts as missing.
MAX_GSI_NUMBER = 10_000_000


def optional_int(value: Any) -> int | None:
    number = optional_number(value)
    return None if number is None else int(number)


def optional_number(value: Any) -> float | int | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    if not math.isfinite(number) or abs(number) > MAX_GSI_NUMBER:
        return None
    return int(number) if number.is_integer() else number


def optional_bool(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "on"}:
            return True
        if lowered in {"0", "false", "no", "off"}:
            return False
    if isinstance(value, (int, float)):
        return bool(value)
    return None


def optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def first_value(*values: Any) -> Any:
    for value in values:
        if value is not None:
            return value
    return None


def title_from_token(value: str) -> str:
    return value.replace("_", " ").replace("-", " ").title()
