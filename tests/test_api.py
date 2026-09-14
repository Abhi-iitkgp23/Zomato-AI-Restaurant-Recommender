"""FastAPI endpoint tests (Phase 4)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from zomato_rec.app.api import app
from zomato_rec.config import get_settings
from zomato_rec.data.ingest import build_metadata, preprocess_restaurants, save_processed
from zomato_rec.data.repository import clear_cache


@pytest.fixture
def api_client(tmp_path: Path, monkeypatch):
    raw = pd.DataFrame(
        [
            {
                "name": "Pasta House",
                "location": "Banashankari",
                "listed_in(city)": "Banashankari",
                "address": "1 St",
                "url": "https://example.com/10",
                "cuisines": "Italian, Pizza",
                "rate": "4.5/5",
                "votes": 800,
                "approx_cost(for two people)": "650",
                "rest_type": "Casual Dining",
                "dish_liked": "Pasta",
                "online_order": "Yes",
                "book_table": "Yes",
            }
        ]
    )
    cleaned = preprocess_restaurants(raw)
    meta = build_metadata(cleaned)
    data_path = tmp_path / "restaurants.parquet"
    metadata_path = tmp_path / "metadata.json"
    save_processed(cleaned, meta, data_path=data_path, metadata_path=metadata_path)

    monkeypatch.setenv("DATA_PATH", str(data_path))
    monkeypatch.setenv("METADATA_PATH", str(metadata_path))
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    get_settings.cache_clear()
    clear_cache()

    client = TestClient(app)
    yield client
    clear_cache()
    get_settings.cache_clear()


def test_health_ok(api_client):
    res = api_client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert body["data_ready"] is True


def test_meta_locations(api_client):
    res = api_client.get("/meta/locations")
    assert res.status_code == 200
    assert "Banashankari" in res.json()["locations"]


def test_meta_cuisines(api_client):
    res = api_client.get("/meta/cuisines")
    assert res.status_code == 200
    assert "italian" in res.json()["cuisines"]


def test_recommend_validation_error(api_client):
    res = api_client.post("/recommend", json={"budget": "medium"})
    assert res.status_code == 422


def test_recommend_fallback_without_key(api_client):
    res = api_client.post(
        "/recommend",
        json={
            "location": "Banashankari",
            "cuisine": "Italian",
            "budget": "medium",
            "top_n": 3,
            "use_llm": True,
        },
    )
    assert res.status_code == 200
    body = res.json()
    assert body["used_fallback"] is True
    assert body["recommendations"]
    assert body["recommendations"][0]["name"]
