"""Hard filters and candidate selection for the recommend pipeline."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import pandas as pd

from zomato_rec.models import FilterMeta, Preferences, RestaurantCandidate

CANDIDATE_COLUMNS = [
    "id",
    "name",
    "location",
    "cuisines",
    "rating",
    "votes",
    "cost_for_two",
    "rest_type",
    "dish_liked",
    "online_order",
    "book_table",
]

_REST_TYPE_HINTS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bquick\b|\bquick\s*bite", re.I), "quick bites"),
    (re.compile(r"\bcafe\b|\bcoffee\b", re.I), "cafe"),
    (re.compile(r"\bfine\s*dining\b", re.I), "fine dining"),
    (re.compile(r"\bcasual\b", re.I), "casual dining"),
    (re.compile(r"\bdessert\b|\bsweet\b", re.I), "dessert"),
    (re.compile(r"\bbar\b|\bpub\b|\bbrew", re.I), "bar"),
]


@dataclass
class FilterResult:
    candidates: list[RestaurantCandidate]
    frame: pd.DataFrame
    meta: FilterMeta = field(default_factory=FilterMeta)


def _contains_ci(series: pd.Series, needle: str) -> pd.Series:
    return series.fillna("").astype(str).str.contains(
        re.escape(needle), case=False, regex=True
    )


def _apply_hard_filters(
    frame: pd.DataFrame,
    preferences: Preferences,
    *,
    apply_budget: bool,
    apply_rating: bool,
) -> pd.DataFrame:
    out = frame

    if preferences.location:
        out = out[_contains_ci(out["location"], preferences.location)]

    if preferences.cuisine:
        out = out[_contains_ci(out["cuisines"], preferences.cuisine.lower())]

    if apply_budget and preferences.budget:
        out = out[out["budget_band"] == preferences.budget]

    if apply_rating and preferences.min_rating is not None:
        ratings = pd.to_numeric(out["rating"], errors="coerce")
        out = out[ratings >= preferences.min_rating]

    return out


def _apply_rest_type_heuristic(
    frame: pd.DataFrame, free_text: str | None
) -> pd.DataFrame:
    if not free_text or frame.empty:
        return frame

    hints = [token for pattern, token in _REST_TYPE_HINTS if pattern.search(free_text)]
    if not hints:
        return frame

    rest = frame["rest_type"].fillna("").astype(str).str.lower()
    mask = pd.Series(False, index=frame.index)
    for token in hints:
        mask = mask | rest.str.contains(re.escape(token), regex=True)
    narrowed = frame[mask]
    if narrowed.empty:
        return frame
    return narrowed


def _sort_candidates(frame: pd.DataFrame) -> pd.DataFrame:
    return frame.sort_values(
        by=["rating", "votes"],
        ascending=[False, False],
        na_position="last",
    )


def dataframe_to_candidates(frame: pd.DataFrame) -> list[RestaurantCandidate]:
    """Convert a filtered DataFrame slice into candidate models."""
    if frame.empty:
        return []
    cols = [c for c in CANDIDATE_COLUMNS if c in frame.columns]
    records = frame.loc[:, cols].to_dict(orient="records")
    candidates: list[RestaurantCandidate] = []
    for row in records:
        for key in ("rating", "cost_for_two"):
            val = row.get(key)
            if val is not None and isinstance(val, float) and pd.isna(val):
                row[key] = None
        for key in (
            "name",
            "location",
            "cuisines",
            "rest_type",
            "dish_liked",
            "online_order",
            "book_table",
        ):
            val = row.get(key)
            if val is None or (isinstance(val, float) and pd.isna(val)):
                row[key] = ""
            else:
                row[key] = str(val)
        votes = row.get("votes", 0)
        if votes is None or (isinstance(votes, float) and pd.isna(votes)):
            row["votes"] = 0
        else:
            row["votes"] = int(votes)
        row["id"] = int(row["id"])
        if len(row.get("dish_liked", "")) > 200:
            row["dish_liked"] = row["dish_liked"][:200].rstrip() + "…"
        candidates.append(RestaurantCandidate.model_validate(row))
    return candidates


def select_candidates(
    frame: pd.DataFrame,
    preferences: Preferences,
    *,
    candidate_k: int = 15,
) -> FilterResult:
    """Apply hard filters, optional soft heuristics, relaxation, and top-K cap."""
    notices: list[str] = []
    apply_budget = True
    apply_rating = True
    relaxed_budget = False
    relaxed_rating = False

    filtered = _apply_hard_filters(
        frame, preferences, apply_budget=apply_budget, apply_rating=apply_rating
    )

    if filtered.empty and preferences.budget:
        apply_budget = False
        relaxed_budget = True
        notices.append("Relaxed budget filter to find matches.")
        filtered = _apply_hard_filters(
            frame, preferences, apply_budget=apply_budget, apply_rating=apply_rating
        )

    if filtered.empty and preferences.min_rating is not None:
        apply_rating = False
        relaxed_rating = True
        notices.append("Relaxed minimum rating filter to find matches.")
        filtered = _apply_hard_filters(
            frame, preferences, apply_budget=apply_budget, apply_rating=apply_rating
        )

    filtered = _apply_rest_type_heuristic(filtered, preferences.additional_preferences)
    total_before_cap = int(len(filtered))

    if filtered.empty:
        meta = FilterMeta(
            candidate_count=0,
            total_before_cap=0,
            relaxed_budget=relaxed_budget,
            relaxed_rating=relaxed_rating,
            limited_options=False,
            empty=True,
            notices=notices + ["No restaurants matched your preferences."],
        )
        return FilterResult(candidates=[], frame=filtered, meta=meta)

    sorted_frame = _sort_candidates(filtered)
    capped = sorted_frame.head(max(1, candidate_k)).copy()
    limited = total_before_cap < 3
    if limited:
        notices.append(
            f"Only {total_before_cap} matching restaurant(s) found; options are limited."
        )

    candidates = dataframe_to_candidates(capped)
    meta = FilterMeta(
        candidate_count=len(candidates),
        total_before_cap=total_before_cap,
        relaxed_budget=relaxed_budget,
        relaxed_rating=relaxed_rating,
        limited_options=limited,
        empty=False,
        notices=notices,
    )
    return FilterResult(candidates=candidates, frame=capped, meta=meta)
