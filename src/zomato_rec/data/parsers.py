"""Field parsers and budget banding for Zomato dataset rows."""

from __future__ import annotations

import math
import re
from typing import Any

_RATE_PATTERN = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*(?:/\s*5)?\s*$", re.IGNORECASE)
_INVALID_RATES = {"", "new", "-", "nan", "none", "null"}


def parse_rating(value: Any) -> float | None:
    """Parse Zomato `rate` values like ``4.1/5`` into a float.

    Returns ``None`` for ``NEW``, ``-``, missing, or unparseable values.
    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        if isinstance(value, float) and math.isnan(value):
            return None
        return float(value)

    text = str(value).strip()
    if text.lower() in _INVALID_RATES:
        return None

    match = _RATE_PATTERN.match(text)
    if not match:
        return None
    return float(match.group(1))


def parse_cost_for_two(value: Any) -> float | None:
    """Parse ``approx_cost(for two people)``, stripping commas.

    Returns ``None`` for missing, non-numeric, zero, or negative values.
    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        if isinstance(value, float) and math.isnan(value):
            return None
        number = float(value)
        return number if number > 0 else None

    text = str(value).strip().replace(",", "")
    if not text or text.lower() in _INVALID_RATES:
        return None
    try:
        number = float(text)
    except ValueError:
        return None
    return number if number > 0 else None


def normalize_cuisines(value: Any) -> str:
    """Lowercase, comma-separated cuisine string (empty if missing)."""
    if value is None:
        return ""
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "null"}:
        return ""
    parts = [part.strip().lower() for part in text.split(",") if part.strip()]
    return ", ".join(parts)


def budget_band(
    cost_for_two: float | None,
    *,
    low_max: int = 400,
    med_max: int = 800,
) -> str | None:
    """Map cost to ``low`` / ``medium`` / ``high``; ``None`` if cost unknown."""
    if cost_for_two is None:
        return None
    if cost_for_two <= low_max:
        return "low"
    if cost_for_two <= med_max:
        return "medium"
    return "high"


def cuisine_tokens(cuisines: str) -> list[str]:
    """Split a normalized cuisine string into unique tokens."""
    if not cuisines:
        return []
    return [part.strip() for part in cuisines.split(",") if part.strip()]
