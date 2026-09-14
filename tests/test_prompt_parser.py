"""LLM response parser and grounding tests."""

from __future__ import annotations

import pytest

from zomato_rec.llm.parser import (
    ParseError,
    extract_json_object,
    ground_recommendations,
    heuristic_rank,
    parse_llm_payload,
)
from zomato_rec.models import LLMRecommendationPayload, RestaurantCandidate


def _candidates() -> list[RestaurantCandidate]:
    return [
        RestaurantCandidate(
            id=12,
            name="Onesta",
            location="Banashankari",
            cuisines="pizza, italian",
            rating=4.6,
            votes=2556,
            cost_for_two=600,
        ),
        RestaurantCandidate(
            id=13,
            name="Other Place",
            location="Banashankari",
            cuisines="italian",
            rating=4.2,
            votes=100,
            cost_for_two=500,
        ),
    ]


def test_parse_pure_json():
    text = '{"summary": "ok", "recommendations": [{"id": 12, "rank": 1, "name": "Onesta", "explanation": "Great"}]}'
    payload = parse_llm_payload(text)
    assert payload.summary == "ok"
    assert payload.recommendations[0].id == 12


def test_parse_markdown_fenced_json():
    text = """Here you go:
```json
{"summary": "ok", "recommendations": [{"id": 12, "rank": 1, "explanation": "Nice"}]}
```
"""
    payload = parse_llm_payload(text)
    assert payload.recommendations[0].id == 12


def test_parse_leading_prose():
    text = 'Sure! {"summary": "ok", "recommendations": [{"id": 13, "rank": 1, "explanation": "x"}]} thanks'
    data = extract_json_object(text)
    assert data["summary"] == "ok"


def test_invalid_json_raises():
    with pytest.raises(ParseError):
        parse_llm_payload("not json at all")


def test_drop_hallucinated_ids():
    payload = LLMRecommendationPayload.model_validate(
        {
            "summary": "mix",
            "recommendations": [
                {"id": 999, "rank": 1, "name": "Fake", "explanation": "nope"},
                {"id": 12, "rank": 2, "name": "WrongName", "explanation": "real"},
            ],
        }
    )
    items, summary = ground_recommendations(payload, _candidates(), top_n=5)
    assert len(items) == 1
    assert items[0].id == 12
    assert items[0].name == "Onesta"  # dataset name wins
    assert items[0].rank == 1
    assert summary == "mix"


def test_truncate_to_top_n():
    payload = LLMRecommendationPayload.model_validate(
        {
            "summary": "many",
            "recommendations": [
                {"id": 12, "rank": 1, "explanation": "a"},
                {"id": 13, "rank": 2, "explanation": "b"},
            ],
        }
    )
    items, _ = ground_recommendations(payload, _candidates(), top_n=1)
    assert len(items) == 1
    assert items[0].id == 12


def test_missing_explanation_uses_template():
    payload = LLMRecommendationPayload.model_validate(
        {"summary": None, "recommendations": [{"id": 12, "rank": 1}]}
    )
    items, summary = ground_recommendations(payload, _candidates(), top_n=5)
    assert "Onesta" in items[0].explanation
    assert "Banashankari" in items[0].explanation
    assert summary


def test_heuristic_rank_order():
    items, summary = heuristic_rank(_candidates(), top_n=2)
    assert [i.id for i in items] == [12, 13]
    assert "AI ranking unavailable" in summary
    assert items[0].rating == 4.6
