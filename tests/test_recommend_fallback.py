"""Recommend service: mocked LLM happy path and fallback."""

from __future__ import annotations

import json

import pandas as pd
import pytest

from zomato_rec.config import Settings
from zomato_rec.llm.client import LLMError
from zomato_rec.models import Preferences
from zomato_rec.services.recommend import recommend


def _restaurants() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "id": 10,
                "name": "Pasta House",
                "location": "Banashankari",
                "listed_in_city": "Banashankari",
                "address": "1 St",
                "url": "https://example.com/10",
                "cuisines": "italian, pizza",
                "rating": 4.5,
                "votes": 800,
                "cost_for_two": 650,
                "budget_band": "medium",
                "rest_type": "Casual Dining",
                "dish_liked": "Pasta",
                "online_order": "Yes",
                "book_table": "Yes",
            },
            {
                "id": 11,
                "name": "Noodle Bar",
                "location": "Banashankari",
                "listed_in_city": "Banashankari",
                "address": "2 St",
                "url": "https://example.com/11",
                "cuisines": "chinese",
                "rating": 4.2,
                "votes": 200,
                "cost_for_two": 500,
                "budget_band": "medium",
                "rest_type": "Casual Dining",
                "dish_liked": "Noodles",
                "online_order": "Yes",
                "book_table": "No",
            },
        ]
    )


def _settings() -> Settings:
    return Settings(
        llm_provider="openai",
        llm_api_key=None,
        llm_model="gpt-4o-mini",
        data_path=__import__("pathlib").Path("unused.parquet"),
        metadata_path=__import__("pathlib").Path("unused.json"),
        candidate_k=15,
        default_top_n=5,
        budget_low_max=400,
        budget_med_max=800,
        hf_dataset_id="test",
        hf_dataset_revision=None,
    )


class _FakeLLM:
    def __init__(self, text: str | None = None, error: Exception | None = None):
        self.text = text
        self.error = error
        self.calls = 0

    def complete(self, messages: list[dict], *, temperature: float = 0.2) -> str:
        self.calls += 1
        if self.error:
            raise self.error
        assert self.text is not None
        return self.text


def test_recommend_with_mocked_llm():
    payload = {
        "summary": "Italian picks in Banashankari.",
        "recommendations": [
            {
                "id": 10,
                "rank": 1,
                "name": "Pasta House",
                "explanation": "Strong Italian match with solid rating.",
            }
        ],
    }
    client = _FakeLLM(text=json.dumps(payload))
    prefs = Preferences(
        location="Banashankari",
        cuisine="Italian",
        budget="medium",
        min_rating=4.0,
        top_n=3,
    )
    result = recommend(
        prefs,
        restaurants=_restaurants(),
        settings=_settings(),
        llm_client=client,
    )
    assert result.used_fallback is False
    assert client.calls == 1
    assert len(result.recommendations) == 1
    assert result.recommendations[0].id == 10
    assert result.recommendations[0].name == "Pasta House"
    assert "Italian" in result.recommendations[0].explanation or "italian" in result.recommendations[0].cuisine
    assert result.filter_meta.candidate_count >= 1


def test_recommend_fallback_on_llm_error():
    client = _FakeLLM(error=LLMError("timeout"))
    prefs = Preferences(location="Banashankari", cuisine="Italian", budget="medium")
    result = recommend(
        prefs,
        restaurants=_restaurants(),
        settings=_settings(),
        llm_client=client,
    )
    assert result.used_fallback is True
    assert result.recommendations
    assert result.recommendations[0].id == 10
    assert "AI ranking unavailable" in result.summary or "matches" in result.recommendations[0].explanation


def test_recommend_fallback_when_no_llm():
    prefs = Preferences(location="Banashankari", cuisine="Chinese")
    result = recommend(
        prefs,
        restaurants=_restaurants(),
        settings=_settings(),
        use_llm=False,
    )
    assert result.used_fallback is True
    assert result.recommendations[0].id == 11


def test_recommend_empty_preferences_path():
    prefs = Preferences(location="Nowhereville", cuisine="Martian")
    result = recommend(
        prefs,
        restaurants=_restaurants(),
        settings=_settings(),
        use_llm=False,
    )
    assert result.recommendations == []
    assert result.filter_meta.empty is True


def test_recommend_drops_hallucinated_id_then_still_returns_grounded():
    payload = {
        "summary": "mixed",
        "recommendations": [
            {"id": 999, "rank": 1, "explanation": "fake"},
            {"id": 10, "rank": 2, "explanation": "real pick"},
        ],
    }
    result = recommend(
        Preferences(location="Banashankari", cuisine="Italian"),
        restaurants=_restaurants(),
        settings=_settings(),
        llm_client=_FakeLLM(text=json.dumps(payload)),
    )
    assert [r.id for r in result.recommendations] == [10]
    assert result.used_fallback is False


def test_recommend_invalid_key_style_error_falls_back():
    """Auth-style LLM failures must still return heuristic results."""
    from zomato_rec.llm.client import LLMError

    class _AuthFail:
        def complete(self, messages, *, temperature: float = 0.2) -> str:
            raise LLMError("Error code: 401 - Invalid API Key")

    prefs = Preferences(location="Banashankari", cuisine="Italian", budget="medium")
    result = recommend(
        prefs,
        restaurants=_restaurants(),
        settings=_settings(),
        llm_client=_AuthFail(),
    )
    assert result.used_fallback is True
    assert result.recommendations
    assert "401" in (result.fallback_reason or "")
