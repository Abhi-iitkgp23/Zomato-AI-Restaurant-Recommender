"""Filter layer tests: hard filters, relaxation, capping."""

from __future__ import annotations

import pandas as pd
import pytest

from zomato_rec.filtering.filters import select_candidates
from zomato_rec.models import Preferences


def _frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "id": 1,
                "name": "Onesta",
                "location": "Banashankari",
                "cuisines": "pizza, cafe, italian",
                "rating": 4.6,
                "votes": 2556,
                "cost_for_two": 600,
                "budget_band": "medium",
                "rest_type": "Casual Dining, Cafe",
                "dish_liked": "Farmhouse Pizza",
                "online_order": "Yes",
                "book_table": "Yes",
                "address": "a1",
                "url": "u1",
            },
            {
                "id": 2,
                "name": "Cheap Italian",
                "location": "Banashankari",
                "cuisines": "italian",
                "rating": 4.1,
                "votes": 100,
                "cost_for_two": 300,
                "budget_band": "low",
                "rest_type": "Quick Bites",
                "dish_liked": "Pasta",
                "online_order": "Yes",
                "book_table": "No",
                "address": "a2",
                "url": "u2",
            },
            {
                "id": 3,
                "name": "Fancy Spot",
                "location": "Indiranagar",
                "cuisines": "japanese",
                "rating": 4.8,
                "votes": 500,
                "cost_for_two": 1500,
                "budget_band": "high",
                "rest_type": "Fine Dining",
                "dish_liked": "Sushi",
                "online_order": "No",
                "book_table": "Yes",
                "address": "a3",
                "url": "u3",
            },
            {
                "id": 4,
                "name": "Low Rated Italian",
                "location": "Banashankari",
                "cuisines": "italian",
                "rating": 3.2,
                "votes": 50,
                "cost_for_two": 550,
                "budget_band": "medium",
                "rest_type": "Casual Dining",
                "dish_liked": "",
                "online_order": "Yes",
                "book_table": "No",
                "address": "a4",
                "url": "u4",
            },
            {
                "id": 5,
                "name": "Null Rating Cafe",
                "location": "Banashankari",
                "cuisines": "cafe",
                "rating": None,
                "votes": 10,
                "cost_for_two": 400,
                "budget_band": "low",
                "rest_type": "Cafe",
                "dish_liked": "Coffee",
                "online_order": "Yes",
                "book_table": "No",
                "address": "a5",
                "url": "u5",
            },
        ]
    )


def test_happy_path_filters():
    prefs = Preferences(
        location="Banashankari",
        cuisine="Italian",
        budget="medium",
        min_rating=4.0,
        top_n=5,
    )
    result = select_candidates(_frame(), prefs, candidate_k=15)
    ids = [c.id for c in result.candidates]
    assert ids == [1]
    assert result.meta.relaxed_budget is False
    assert result.meta.empty is False


def test_cap_to_k():
    prefs = Preferences(location="Banashankari", cuisine=None, top_n=5)
    result = select_candidates(_frame(), prefs, candidate_k=2)
    assert len(result.candidates) == 2
    assert result.meta.total_before_cap >= 2
    # Highest rating first among Banashankari with ratings
    assert result.candidates[0].id == 1


def test_relax_budget_then_find_matches():
    prefs = Preferences(
        location="Banashankari",
        cuisine="Italian",
        budget="high",  # no high Italian in Banashankari
        min_rating=4.0,
    )
    result = select_candidates(_frame(), prefs, candidate_k=15)
    assert result.meta.relaxed_budget is True
    assert {c.id for c in result.candidates} == {1, 2}


def test_relax_rating_after_budget():
    prefs = Preferences(
        location="Banashankari",
        cuisine="Italian",
        budget="medium",
        min_rating=4.9,  # only Onesta is medium Italian but 4.6 < 4.9
    )
    result = select_candidates(_frame(), prefs, candidate_k=15)
    assert result.meta.relaxed_rating is True
    assert any(c.id == 1 for c in result.candidates)


def test_empty_after_impossible_location():
    prefs = Preferences(location="Atlantis", cuisine="Italian")
    result = select_candidates(_frame(), prefs, candidate_k=15)
    assert result.meta.empty is True
    assert result.candidates == []


def test_limited_options_flag():
    prefs = Preferences(location="Indiranagar", cuisine="Japanese", min_rating=4.0)
    result = select_candidates(_frame(), prefs, candidate_k=15)
    assert result.meta.limited_options is True
    assert len(result.candidates) == 1


def test_soft_rest_type_heuristic_ignored_when_too_strict():
    prefs = Preferences(
        location="Banashankari",
        cuisine="Italian",
        budget="medium",
        additional_preferences="fine dining only please",
    )
    result = select_candidates(_frame(), prefs, candidate_k=15)
    # No fine dining Italian medium in Banashankari — soft filter should not zero out
    assert len(result.candidates) >= 1


def test_null_ratings_do_not_crash_sort():
    prefs = Preferences(location="Banashankari", cuisine="cafe")
    result = select_candidates(_frame(), prefs, candidate_k=15)
    assert any(c.id == 5 for c in result.candidates)


def test_preferences_require_location_or_cuisine():
    with pytest.raises(ValueError, match="location or cuisine"):
        Preferences(budget="medium", min_rating=4.0)


def test_budget_range_filters_cost_for_two():
    prefs = Preferences(location="Banashankari", cuisine="Italian", budget_min=500, budget_max=700)
    result = select_candidates(_frame(), prefs, candidate_k=15)
    assert {c.id for c in result.candidates} == {1, 4}
    assert result.meta.relaxed_budget is False


def test_budget_range_open_ended_max():
    prefs = Preferences(location="Banashankari", budget_min=550)
    result = select_candidates(_frame(), prefs, candidate_k=15)
    assert {c.id for c in result.candidates} == {1, 4}


def test_budget_range_overrides_band():
    prefs = Preferences(location="Banashankari", budget="medium", budget_max=350)
    result = select_candidates(_frame(), prefs, candidate_k=15)
    assert [c.id for c in result.candidates] == [2]


def test_budget_range_relaxes_when_empty():
    prefs = Preferences(location="Banashankari", cuisine="Italian", budget_min=2000)
    result = select_candidates(_frame(), prefs, candidate_k=15)
    assert result.meta.relaxed_budget is True
    assert result.candidates


def test_budget_range_min_above_max_rejected():
    with pytest.raises(ValueError, match="Minimum budget"):
        Preferences(location="Banashankari", budget_min=900, budget_max=500)
