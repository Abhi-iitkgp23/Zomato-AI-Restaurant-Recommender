"""Pydantic models for preferences and recommendations."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

BudgetBand = Literal["low", "medium", "high"]

MAX_ADDITIONAL_PREFERENCES_LEN = 300


class Preferences(BaseModel):
    """User preference payload for filtering and ranking."""

    location: str | None = None
    budget: BudgetBand | None = None
    cuisine: str | None = None
    min_rating: float | None = Field(default=None, ge=0.0, le=5.0)
    additional_preferences: str | None = None
    top_n: int = Field(default=5, ge=1, le=20)

    @field_validator("location", "cuisine", mode="before")
    @classmethod
    def blank_to_none(cls, value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @field_validator("additional_preferences", mode="before")
    @classmethod
    def clean_additional(cls, value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        if not text:
            return None
        if len(text) > MAX_ADDITIONAL_PREFERENCES_LEN:
            text = text[:MAX_ADDITIONAL_PREFERENCES_LEN]
        return text

    @model_validator(mode="after")
    def require_location_or_cuisine(self) -> Preferences:
        if not self.location and not self.cuisine:
            raise ValueError("At least one of location or cuisine is required")
        return self


class RestaurantCandidate(BaseModel):
    """Lean restaurant payload sent to the LLM."""

    id: int
    name: str
    location: str = ""
    cuisines: str = ""
    rating: float | None = None
    votes: int = 0
    cost_for_two: float | None = None
    rest_type: str = ""
    dish_liked: str = ""
    online_order: str = ""
    book_table: str = ""

    model_config = {"extra": "ignore"}


class RecommendationItem(BaseModel):
    """Single ranked recommendation joined to dataset fields."""

    id: int
    rank: int
    name: str
    cuisine: str = ""
    rating: float | None = None
    cost_for_two: float | None = None
    location: str = ""
    explanation: str
    address: str = ""
    url: str = ""
    online_order: str = ""
    book_table: str = ""
    rest_type: str = ""


class LLMRecommendationItem(BaseModel):
    """Raw item shape expected from the LLM JSON payload."""

    id: int
    rank: int | None = None
    name: str | None = None
    explanation: str | None = None

    model_config = {"extra": "ignore"}


class LLMRecommendationPayload(BaseModel):
    """Parsed LLM response before grounding/join."""

    summary: str | None = None
    recommendations: list[LLMRecommendationItem] = Field(default_factory=list)

    model_config = {"extra": "ignore"}


class FilterMeta(BaseModel):
    """Diagnostics about the filter / relaxation path."""

    candidate_count: int = 0
    total_before_cap: int = 0
    relaxed_budget: bool = False
    relaxed_rating: bool = False
    limited_options: bool = False
    empty: bool = False
    notices: list[str] = Field(default_factory=list)


class RecommendationResponse(BaseModel):
    """End-to-end recommend() result for CLI / UI."""

    summary: str = ""
    recommendations: list[RecommendationItem] = Field(default_factory=list)
    filter_meta: FilterMeta = Field(default_factory=FilterMeta)
    used_fallback: bool = False
    fallback_reason: str | None = None
    latency_ms: float | None = None
