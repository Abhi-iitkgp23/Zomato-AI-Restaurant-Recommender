"""Safe logging helpers — never log secrets or full prompts."""

from __future__ import annotations

import hashlib
import logging
from typing import Any

from zomato_rec.models import Preferences

logger = logging.getLogger("zomato_rec.observability")


def preference_hash(preferences: Preferences) -> str:
    """Stable short hash of preferences for correlation (not reversible to free-text easily)."""
    payload = preferences.model_dump_json(exclude_none=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _budget_label(preferences: Preferences) -> str:
    if preferences.has_budget_range:
        low = f"{preferences.budget_min:.0f}" if preferences.budget_min is not None else "0"
        high = f"{preferences.budget_max:.0f}" if preferences.budget_max is not None else "max"
        return f"{low}-{high}"
    return preferences.budget or "-"


def log_recommend_event(
    *,
    preferences: Preferences,
    candidate_count: int,
    latency_ms: float,
    used_fallback: bool,
    parse_ok: bool | None,
    empty: bool,
    provider: str | None = None,
) -> None:
    """Emit a single structured-ish info line for a recommend request."""
    logger.info(
        "recommend prefs_hash=%s location=%s cuisine=%s budget=%s "
        "candidates=%s empty=%s parse_ok=%s fallback=%s latency_ms=%.0f provider=%s",
        preference_hash(preferences),
        preferences.location or "-",
        preferences.cuisine or "-",
        _budget_label(preferences),
        candidate_count,
        empty,
        parse_ok,
        used_fallback,
        latency_ms,
        provider or "-",
    )


def redact_secrets(mapping: dict[str, Any]) -> dict[str, Any]:
    """Return a copy with secret-like values redacted (for debug dumps)."""
    secret_keys = {"api_key", "llm_api_key", "authorization", "password", "token"}
    out: dict[str, Any] = {}
    for key, value in mapping.items():
        if key.lower() in secret_keys or "api_key" in key.lower():
            out[key] = "***"
        else:
            out[key] = value
    return out
