"""Extract and validate LLM recommendation JSON; ground to candidate IDs."""

from __future__ import annotations

import json
import re
from typing import Any

from zomato_rec.models import (
    LLMRecommendationPayload,
    RecommendationItem,
    RestaurantCandidate,
)

_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.IGNORECASE)


class ParseError(ValueError):
    """Raised when LLM output cannot be parsed into the expected schema."""


def extract_json_object(text: str) -> dict[str, Any]:
    """Parse a JSON object from raw model text (fences / leading prose OK)."""
    if not text or not text.strip():
        raise ParseError("Empty LLM text")

    stripped = text.strip()

    fence = _FENCE_RE.search(stripped)
    if fence:
        stripped = fence.group(1).strip()

    try:
        data = json.loads(stripped)
    except json.JSONDecodeError:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start < 0 or end <= start:
            raise ParseError("No JSON object found in LLM response") from None
        try:
            data = json.loads(stripped[start : end + 1])
        except json.JSONDecodeError as exc:
            raise ParseError(f"Invalid JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise ParseError("LLM JSON root must be an object")
    return data


def parse_llm_payload(text: str) -> LLMRecommendationPayload:
    """Validate extracted JSON against the LLM recommendation schema."""
    data = extract_json_object(text)
    try:
        return LLMRecommendationPayload.model_validate(data)
    except Exception as exc:  # pydantic ValidationError
        raise ParseError(f"Schema validation failed: {exc}") from exc


def ground_recommendations(
    payload: LLMRecommendationPayload,
    candidates: list[RestaurantCandidate],
    *,
    top_n: int,
    restaurant_lookup: dict[int, dict[str, Any]] | None = None,
) -> tuple[list[RecommendationItem], str]:
    """Keep only known candidate IDs; join dataset fields; enforce top_n.

    Returns ``(items, summary)``.
    """
    by_id = {c.id: c for c in candidates}
    seen: set[int] = set()
    grounded: list[RecommendationItem] = []

    # Prefer LLM rank order; fall back to array order.
    ordered = sorted(
        enumerate(payload.recommendations),
        key=lambda pair: (
            pair[1].rank is None,
            pair[1].rank if pair[1].rank is not None else pair[0],
            pair[0],
        ),
    )

    for _, item in ordered:
        if item.id not in by_id or item.id in seen:
            continue
        seen.add(item.id)
        candidate = by_id[item.id]
        extra = (restaurant_lookup or {}).get(item.id, {})
        explanation = (item.explanation or "").strip() or _template_explanation(
            candidate, cuisine_hint=candidate.cuisines
        )
        grounded.append(
            RecommendationItem(
                id=candidate.id,
                rank=len(grounded) + 1,
                name=candidate.name,
                cuisine=candidate.cuisines,
                rating=candidate.rating,
                cost_for_two=candidate.cost_for_two,
                location=candidate.location,
                explanation=explanation,
                address=str(extra.get("address") or ""),
                url=str(extra.get("url") or ""),
                online_order=candidate.online_order,
                book_table=candidate.book_table,
                rest_type=candidate.rest_type,
            )
        )
        if len(grounded) >= top_n:
            break

    summary = (payload.summary or "").strip()
    if not summary and grounded:
        summary = f"Top {len(grounded)} recommendations from the filtered candidate set."
    return grounded, summary


def _template_explanation(
    candidate: RestaurantCandidate, *, cuisine_hint: str = ""
) -> str:
    cuisine = cuisine_hint or candidate.cuisines or "N/A"
    rating = candidate.rating if candidate.rating is not None else "N/A"
    cost = (
        f"₹{int(candidate.cost_for_two)}"
        if candidate.cost_for_two is not None
        else "N/A"
    )
    location = candidate.location or "N/A"
    return (
        f"{candidate.name} matches {cuisine} in {location} "
        f"with rating {rating} and approx cost {cost}."
    )


def heuristic_rank(
    candidates: list[RestaurantCandidate],
    *,
    top_n: int,
    cuisine_hint: str | None = None,
    restaurant_lookup: dict[int, dict[str, Any]] | None = None,
) -> tuple[list[RecommendationItem], str]:
    """Rank by rating then votes; emit template explanations."""
    ordered = sorted(
        candidates,
        key=lambda c: (
            c.rating is None,
            -(c.rating or 0.0),
            -c.votes,
            c.id,
        ),
    )
    items: list[RecommendationItem] = []
    for candidate in ordered[:top_n]:
        extra = (restaurant_lookup or {}).get(candidate.id, {})
        items.append(
            RecommendationItem(
                id=candidate.id,
                rank=len(items) + 1,
                name=candidate.name,
                cuisine=candidate.cuisines,
                rating=candidate.rating,
                cost_for_two=candidate.cost_for_two,
                location=candidate.location,
                explanation=_template_explanation(
                    candidate, cuisine_hint=cuisine_hint or candidate.cuisines
                ),
                address=str(extra.get("address") or ""),
                url=str(extra.get("url") or ""),
                online_order=candidate.online_order,
                book_table=candidate.book_table,
                rest_type=candidate.rest_type,
            )
        )
    summary = (
        f"Showing {len(items)} popularity-based recommendations "
        "(AI ranking unavailable)."
        if items
        else "No recommendations available."
    )
    return items, summary
