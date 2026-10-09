"""Strict JSON decoding and the minimum shapes expected from cached values."""

from __future__ import annotations

import json
import math
from typing import Any


def _finite_float(raw: str) -> float:
    value = float(raw)
    if not math.isfinite(value):
        raise ValueError("Non-finite JSON number")
    return value


def _reject_constant(raw: str) -> Any:
    raise ValueError("Non-finite JSON constant")


def load_json(raw: str) -> Any:
    value = json.loads(raw, parse_float=_finite_float, parse_constant=_reject_constant)
    pending = [value]
    while pending:
        part = pending.pop()
        if isinstance(part, str):
            part.encode("utf-8")  # Reject lone surrogates before HTTP/UI serialization.
        elif isinstance(part, list):
            pending.extend(part)
        elif isinstance(part, dict):
            pending.extend(part.keys())
            pending.extend(part.values())
    return value


def cache_value_valid(key: str, value: Any) -> bool:
    """Check containers used by consumers, without fixing a review/rules version."""
    if value is None:
        return True  # Existing callers use JSON null to invalidate an entry.
    if key.startswith(("coach:ask:", "opendota:item_timings:")) or key == "opendota:hero_stats":
        return isinstance(value, list) and all(isinstance(row, dict) for row in value)
    if key.startswith("friend:matches:"):
        return (
            isinstance(value, dict)
            and (value.get("profile") is None or isinstance(value["profile"], dict))
            and (
                value.get("matches") is None
                or (
                    isinstance(value["matches"], list)
                    and all(isinstance(row, dict) for row in value["matches"])
                )
            )
        )
    if key.startswith("coach:"):
        return (
            isinstance(value, dict)
            and (value.get("review") is None or isinstance(value["review"], dict))
            and all(
                value.get(field) is None or isinstance(value[field], str)
                for field in ("hash", "provider", "model", "generated_at")
            )
        )
    if key == "opendota:items" or key.startswith(
        ("opendota:item_popularity:", "opendota:pro_skills:", "opendota:matchups:")
    ):
        return isinstance(value, dict)
    return True
