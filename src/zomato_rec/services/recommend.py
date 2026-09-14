"""End-to-end recommendation orchestration."""

from __future__ import annotations

import logging
import time
from typing import Any

import pandas as pd

from zomato_rec.config import Settings, get_settings
from zomato_rec.data.repository import load_restaurants
from zomato_rec.filtering.filters import select_candidates
from zomato_rec.llm.client import LLMClient, LLMError, get_llm_client
from zomato_rec.llm.parser import (
    ParseError,
    ground_recommendations,
    heuristic_rank,
    parse_llm_payload,
)
from zomato_rec.llm.prompts import build_messages
from zomato_rec.models import Preferences, RecommendationItem, RecommendationResponse
from zomato_rec.observability import log_recommend_event
from zomato_rec.safety import sanitize_text

logger = logging.getLogger(__name__)


def _lookup_from_frame(frame: pd.DataFrame) -> dict[int, dict[str, Any]]:
    lookup: dict[int, dict[str, Any]] = {}
    if frame.empty:
        return lookup
    for row in frame.to_dict(orient="records"):
        rid = int(row["id"])
        lookup[rid] = {
            "address": row.get("address") or "",
            "url": row.get("url") or "",
        }
    return lookup


def _sanitize_items(items: list[RecommendationItem]) -> list[RecommendationItem]:
    cleaned: list[RecommendationItem] = []
    for item in items:
        data = item.model_dump()
        data["explanation"] = sanitize_text(item.explanation, max_len=1500)
        data["name"] = sanitize_text(item.name, max_len=200)
        cleaned.append(RecommendationItem.model_validate(data))
    return cleaned


def recommend(
    preferences: Preferences | dict[str, Any],
    *,
    restaurants: pd.DataFrame | None = None,
    settings: Settings | None = None,
    llm_client: LLMClient | None = None,
    use_llm: bool = True,
) -> RecommendationResponse:
    """Filter candidates, rank via LLM (or heuristic fallback), return top-N."""
    started = time.perf_counter()
    settings = settings or get_settings()

    if isinstance(preferences, dict):
        preferences = Preferences.model_validate(preferences)

    frame = restaurants if restaurants is not None else load_restaurants()
    filter_result = select_candidates(
        frame, preferences, candidate_k=settings.candidate_k
    )
    lookup = _lookup_from_frame(filter_result.frame)
    top_n = min(preferences.top_n, settings.candidate_k)
    provider = settings.llm_provider

    def _finish(
        *,
        summary: str,
        recommendations: list[RecommendationItem],
        used_fallback: bool,
        fallback_reason: str | None,
        parse_ok: bool | None,
    ) -> RecommendationResponse:
        latency_ms = (time.perf_counter() - started) * 1000
        response = RecommendationResponse(
            summary=sanitize_text(summary, max_len=1000),
            recommendations=_sanitize_items(recommendations),
            filter_meta=filter_result.meta,
            used_fallback=used_fallback,
            fallback_reason=fallback_reason,
            latency_ms=latency_ms,
        )
        log_recommend_event(
            preferences=preferences,
            candidate_count=filter_result.meta.candidate_count,
            latency_ms=latency_ms,
            used_fallback=used_fallback,
            parse_ok=parse_ok,
            empty=filter_result.meta.empty,
            provider=provider,
        )
        return response

    if filter_result.meta.empty or not filter_result.candidates:
        return _finish(
            summary="No restaurants matched your preferences.",
            recommendations=[],
            used_fallback=False,
            fallback_reason=None,
            parse_ok=None,
        )

    # Heuristic path when LLM disabled / unavailable.
    client = llm_client
    if use_llm and client is None:
        try:
            client = get_llm_client(settings)
        except LLMError as exc:
            logger.warning("LLM client init failed: %s", exc)
            client = None

    if not use_llm or client is None:
        items, summary = heuristic_rank(
            filter_result.candidates,
            top_n=top_n,
            cuisine_hint=preferences.cuisine,
            restaurant_lookup=lookup,
        )
        if filter_result.meta.notices:
            notice = " ".join(filter_result.meta.notices)
            summary = f"{summary} {notice}".strip()
        reason = "LLM disabled" if not use_llm else "LLM credentials/client unavailable"
        return _finish(
            summary=summary,
            recommendations=items,
            used_fallback=True,
            fallback_reason=reason,
            parse_ok=False,
        )

    messages = build_messages(
        preferences,
        filter_result.candidates,
        limited_options=filter_result.meta.limited_options,
        relaxed_budget=filter_result.meta.relaxed_budget,
        relaxed_rating=filter_result.meta.relaxed_rating,
    )

    try:
        raw = client.complete(messages, temperature=0.2)
        payload = parse_llm_payload(raw)
        items, summary = ground_recommendations(
            payload,
            filter_result.candidates,
            top_n=top_n,
            restaurant_lookup=lookup,
        )
        if not items:
            raise ParseError("No grounded recommendations after ID validation")
        return _finish(
            summary=summary,
            recommendations=items,
            used_fallback=False,
            fallback_reason=None,
            parse_ok=True,
        )
    except (LLMError, ParseError) as exc:
        logger.warning("LLM recommend path failed (%s); using heuristic fallback", exc)
        items, summary = heuristic_rank(
            filter_result.candidates,
            top_n=top_n,
            cuisine_hint=preferences.cuisine,
            restaurant_lookup=lookup,
        )
        return _finish(
            summary=summary,
            recommendations=items,
            used_fallback=True,
            fallback_reason=str(exc),
            parse_ok=False,
        )
    except Exception as exc:  # noqa: BLE001 — keep app resilient
        logger.warning(
            "Unexpected recommend failure (%s); using heuristic fallback",
            type(exc).__name__,
        )
        items, summary = heuristic_rank(
            filter_result.candidates,
            top_n=top_n,
            cuisine_hint=preferences.cuisine,
            restaurant_lookup=lookup,
        )
        return _finish(
            summary=summary,
            recommendations=items,
            used_fallback=True,
            fallback_reason=f"{type(exc).__name__}: {exc}",
            parse_ok=False,
        )
