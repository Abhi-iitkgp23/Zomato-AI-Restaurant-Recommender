"""Unit tests for rating/cost parsers and budget banding."""

from __future__ import annotations

import pandas as pd
import pytest

from zomato_rec.data.ingest import build_metadata, preprocess_restaurants
from zomato_rec.data.parsers import (
    budget_band,
    cuisine_tokens,
    normalize_cuisines,
    parse_cost_for_two,
    parse_rating,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("4.1/5", 4.1),
        ("4.1", 4.1),
        (" 3.9/5 ", 3.9),
        (4.5, 4.5),
        ("NEW", None),
        ("new", None),
        ("-", None),
        (None, None),
        ("", None),
        ("Good", None),
        (float("nan"), None),
        ("0/5", 0.0),
    ],
)
def test_parse_rating(raw, expected):
    result = parse_rating(raw)
    if expected is None:
        assert result is None
    else:
        assert result == pytest.approx(expected)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("600", 600.0),
        ("1,200", 1200.0),
        ("600.0", 600.0),
        (800, 800.0),
        (None, None),
        ("", None),
        ("abc", None),
        (0, None),
        (-10, None),
        (float("nan"), None),
    ],
)
def test_parse_cost_for_two(raw, expected):
    result = parse_cost_for_two(raw)
    if expected is None:
        assert result is None
    else:
        assert result == pytest.approx(expected)


@pytest.mark.parametrize(
    ("cost", "expected"),
    [
        (400, "low"),
        (200, "low"),
        (401, "medium"),
        (800, "medium"),
        (801, "high"),
        (1200, "high"),
        (None, None),
    ],
)
def test_budget_band_boundaries(cost, expected):
    assert budget_band(cost, low_max=400, med_max=800) == expected


def test_normalize_cuisines():
    assert normalize_cuisines("Pizza, Cafe, Italian") == "pizza, cafe, italian"
    assert normalize_cuisines("Pizza,  Cafe") == "pizza, cafe"
    assert normalize_cuisines(None) == ""
    assert normalize_cuisines("") == ""
    assert cuisine_tokens("pizza, cafe") == ["pizza", "cafe"]


def _sample_raw() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "name": "Onesta",
                "location": "Banashankari",
                "listed_in(city)": "Banashankari",
                "address": "123 Main St",
                "url": "https://example.com/1",
                "cuisines": "Pizza, Cafe, Italian",
                "rate": "4.6/5",
                "votes": 2556,
                "approx_cost(for two people)": "600",
                "rest_type": "Casual Dining, Cafe",
                "dish_liked": "Farmhouse Pizza",
                "online_order": "Yes",
                "book_table": "Yes",
                "menu_item": ["ignored"],
            },
            {
                "name": "Onesta",
                "location": "Banashankari",
                "listed_in(city)": "Banashankari",
                "address": "123 Main St",
                "url": "https://example.com/1-dup",
                "cuisines": "Pizza, Italian",
                "rate": "4.5/5",
                "votes": 100,
                "approx_cost(for two people)": "600",
                "rest_type": "Cafe",
                "dish_liked": "",
                "online_order": "Yes",
                "book_table": "No",
                "menu_item": [],
            },
            {
                "name": "Budget Bites",
                "location": "Jayanagar",
                "listed_in(city)": "Jayanagar",
                "address": "45 Low St",
                "url": "https://example.com/2",
                "cuisines": "North Indian",
                "rate": "NEW",
                "votes": 10,
                "approx_cost(for two people)": "350",
                "rest_type": "Quick Bites",
                "dish_liked": None,
                "online_order": "No",
                "book_table": "No",
                "menu_item": None,
            },
            {
                "name": "High End",
                "location": "Indiranagar",
                "listed_in(city)": "Indiranagar",
                "address": "9 Fancy Ave",
                "url": "https://example.com/3",
                "cuisines": "Japanese",
                "rate": "-",
                "votes": 50,
                "approx_cost(for two people)": "1,200",
                "rest_type": "Fine Dining",
                "dish_liked": "Sushi",
                "online_order": "No",
                "book_table": "Yes",
                "menu_item": None,
            },
            {
                "name": "",
                "location": "Nowhere",
                "listed_in(city)": "Nowhere",
                "address": "x",
                "url": "",
                "cuisines": "Chinese",
                "rate": "4.0/5",
                "votes": 1,
                "approx_cost(for two people)": "500",
                "rest_type": "Casual Dining",
                "dish_liked": "",
                "online_order": "Yes",
                "book_table": "No",
                "menu_item": None,
            },
        ]
    )


def test_preprocess_dedup_and_banding():
    cleaned = preprocess_restaurants(_sample_raw())
    assert len(cleaned) == 3  # empty name dropped; Onesta deduped
    assert set(cleaned["name"]) == {"Onesta", "Budget Bites", "High End"}

    onesta = cleaned.loc[cleaned["name"] == "Onesta"].iloc[0]
    assert onesta["votes"] == 2556  # kept higher-votes duplicate
    assert onesta["rating"] == pytest.approx(4.6)
    assert onesta["cost_for_two"] == pytest.approx(600)
    assert onesta["budget_band"] == "medium"
    assert onesta["cuisines"] == "pizza, cafe, italian"
    assert "menu_item" not in cleaned.columns

    budget = cleaned.loc[cleaned["name"] == "Budget Bites"].iloc[0]
    assert pd.isna(budget["rating"])
    assert budget["budget_band"] == "low"

    high = cleaned.loc[cleaned["name"] == "High End"].iloc[0]
    assert high["cost_for_two"] == pytest.approx(1200)
    assert high["budget_band"] == "high"


def test_build_metadata_vocabularies():
    cleaned = preprocess_restaurants(_sample_raw())
    meta = build_metadata(cleaned)
    assert meta["row_count"] == 3
    assert meta["schema_version"] == 1
    assert "Banashankari" in meta["locations"]
    assert "italian" in meta["cuisines"]
    assert "pizza" in meta["cuisines"]
    assert meta["budget_band_counts"]["medium"] >= 1


def test_preprocess_rejects_empty_result():
    emptyish = pd.DataFrame(
        [
            {
                "name": "",
                "location": "x",
                "listed_in(city)": "x",
                "address": "",
                "url": "",
                "cuisines": "",
                "rate": "NEW",
                "votes": 0,
                "approx_cost(for two people)": None,
                "rest_type": "",
                "dish_liked": "",
                "online_order": "",
                "book_table": "",
            }
        ]
    )
    with pytest.raises(ValueError, match="empty"):
        preprocess_restaurants(emptyish)
