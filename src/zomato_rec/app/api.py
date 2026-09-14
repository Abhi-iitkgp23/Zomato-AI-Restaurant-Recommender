"""FastAPI wrapper sharing the same recommend service layer (Phase 4)."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, ValidationError

from zomato_rec.config import get_settings
from zomato_rec.data.repository import (
    DataNotPreparedError,
    list_cuisines,
    list_locations,
    load_metadata,
    load_restaurants,
)
from zomato_rec.models import Preferences, RecommendationResponse
from zomato_rec.safety import sanitize_text
from zomato_rec.services.recommend import recommend

app = FastAPI(
    title="Zomato Restaurant Recommender API",
    version="0.1.0",
    description="Filter + Groq/LLM ranking over the cached Zomato HF dataset.",
)


class RecommendRequest(BaseModel):
    location: str | None = None
    budget: str | None = None
    cuisine: str | None = None
    min_rating: float | None = Field(default=None, ge=0.0, le=5.0)
    additional_preferences: str | None = None
    top_n: int = Field(default=5, ge=1, le=20)
    use_llm: bool = True


def _safe_response(result: RecommendationResponse) -> dict[str, Any]:
    """Serialize recommendations with HTML-escaped free text for web clients."""
    data = result.model_dump(mode="json")
    data["summary"] = sanitize_text(result.summary, escape=True, max_len=1000)
    for item in data.get("recommendations", []):
        item["explanation"] = sanitize_text(
            item.get("explanation"), escape=True, max_len=1500
        )
        item["name"] = sanitize_text(item.get("name"), escape=True, max_len=200)
    return data


@app.get("/health")
def health() -> dict[str, Any]:
    settings = get_settings(validate=False)
    parquet_ok = settings.data_path.is_file()
    meta_ok = settings.metadata_path.is_file()
    status = "ok" if parquet_ok and meta_ok else "degraded"
    return {
        "status": status,
        "provider": settings.llm_provider,
        "model": settings.llm_model,
        "has_llm_credentials": settings.has_llm_credentials,
        "data_ready": parquet_ok and meta_ok,
        "parquet_exists": parquet_ok,
        "metadata_exists": meta_ok,
    }


@app.get("/meta/locations")
def meta_locations() -> dict[str, Any]:
    try:
        return {"locations": list_locations()}
    except DataNotPreparedError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/meta/cuisines")
def meta_cuisines() -> dict[str, Any]:
    try:
        return {"cuisines": list_cuisines()}
    except DataNotPreparedError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/meta")
def meta_summary() -> dict[str, Any]:
    try:
        meta = load_metadata()
        return {
            "row_count": meta.get("row_count"),
            "schema_version": meta.get("schema_version"),
            "location_count": len(meta.get("locations", [])),
            "cuisine_count": len(meta.get("cuisines", [])),
            "budget_band_counts": meta.get("budget_band_counts", {}),
        }
    except DataNotPreparedError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/recommend")
def post_recommend(body: RecommendRequest) -> dict[str, Any]:
    try:
        preferences = Preferences(
            location=body.location,
            budget=body.budget,  # type: ignore[arg-type]
            cuisine=body.cuisine,
            min_rating=body.min_rating,
            additional_preferences=body.additional_preferences,
            top_n=body.top_n,
        )
    except ValidationError as exc:
        detail = []
        for err in exc.errors():
            detail.append(
                {
                    "loc": err.get("loc"),
                    "msg": err.get("msg"),
                    "type": err.get("type"),
                }
            )
        raise HTTPException(status_code=422, detail=detail) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    try:
        # Touch data early for a clear 503
        load_restaurants()
        result = recommend(preferences, use_llm=body.use_llm)
    except DataNotPreparedError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Recommend failed: {exc}") from exc

    return _safe_response(result)
