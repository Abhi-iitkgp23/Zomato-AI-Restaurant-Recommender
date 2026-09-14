"""Streamlit UI for preference capture and restaurant recommendations (Phase 3)."""

from __future__ import annotations

import streamlit as st
from pydantic import ValidationError

from zomato_rec.config import get_settings
from zomato_rec.data.repository import (
    DataNotPreparedError,
    list_cuisines,
    list_locations,
    load_metadata,
)
from zomato_rec.models import Preferences, RecommendationResponse
from zomato_rec.services.recommend import recommend


def _load_vocab():
    settings = get_settings(validate=False)
    locations = list_locations()
    cuisines = list_cuisines()
    meta = load_metadata()
    return settings, locations, cuisines, meta


def _format_rating(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value:.1f}"


def _format_cost(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"₹{int(value)}"


def _render_notices(result: RecommendationResponse) -> None:
    meta = result.filter_meta
    if meta.notices:
        for notice in meta.notices:
            if meta.empty:
                st.warning(notice)
            else:
                st.info(notice)
    if result.used_fallback:
        reason = result.fallback_reason or "LLM unavailable"
        st.warning(
            "AI ranking via Groq/LLM was unavailable — showing popularity-based "
            f"results instead. ({reason})"
        )


def _render_results(result: RecommendationResponse) -> None:
    _render_notices(result)

    if result.filter_meta.empty or not result.recommendations:
        st.markdown("### No matches")
        st.write(
            "Try a different location or cuisine, lower the minimum rating, "
            "or change the budget band."
        )
        return

    st.markdown("### Summary")
    st.write(result.summary or "Here are your top recommendations.")

    shown = len(result.recommendations)
    st.caption(
        f"{result.filter_meta.candidate_count} candidates → top {shown}"
        + (
            f" (from {result.filter_meta.total_before_cap} before cap)"
            if result.filter_meta.total_before_cap
            else ""
        )
        + (f" · {result.latency_ms:.0f} ms" if result.latency_ms is not None else "")
    )

    for item in result.recommendations:
        with st.container(border=True):
            st.markdown(f"#### {item.rank}. {item.name}")
            cols = st.columns(3)
            cols[0].metric("Rating", _format_rating(item.rating))
            cols[1].metric("Cost for two", _format_cost(item.cost_for_two))
            cols[2].write(f"**Location**  \n{item.location or 'N/A'}")
            st.write(f"**Cuisine:** {item.cuisine or 'N/A'}")
            st.write(f"**Why this fits:** {item.explanation}")
            extras: list[str] = []
            if item.rest_type:
                extras.append(f"Type: {item.rest_type}")
            if item.online_order:
                extras.append(f"Online order: {item.online_order}")
            if item.book_table:
                extras.append(f"Book table: {item.book_table}")
            if extras:
                st.caption(" · ".join(extras))
            if item.address:
                st.caption(item.address)
            if item.url:
                st.link_button("Open on Zomato", item.url, use_container_width=False)


def main() -> None:
    st.set_page_config(
        page_title="Zomato Restaurant Recommender",
        layout="centered",
    )
    st.title("Restaurant Recommender")
    st.write(
        "Filter Bangalore restaurants by your preferences, then rank them with an LLM "
        "(Groq by default)."
    )

    try:
        settings, locations, cuisines, meta = _load_vocab()
    except DataNotPreparedError as exc:
        st.error(str(exc))
        st.code("python scripts/prepare_dataset.py", language="bash")
        st.stop()
    except Exception as exc:  # noqa: BLE001
        st.error(f"Failed to load restaurant metadata: {exc}")
        st.stop()

    with st.sidebar:
        st.header("LLM")
        st.write(f"**Provider:** `{settings.llm_provider}`")
        st.write(f"**Model:** `{settings.llm_model}`")
        if settings.has_llm_credentials:
            st.success("API key configured")
        else:
            st.warning("No API key — heuristic fallback will be used")
        st.caption(f"Dataset rows: {meta.get('row_count', '—')}")
        st.caption(f"Locations: {len(locations)} · Cuisines: {len(cuisines)}")

    if not locations or not cuisines:
        st.error("Location or cuisine vocabulary is empty. Re-run dataset preparation.")
        st.stop()

    with st.form("preferences_form", clear_on_submit=False):
        location = st.selectbox(
            "Location",
            options=["(any)"] + locations,
            index=locations.index("Banashankari") + 1
            if "Banashankari" in locations
            else 0,
        )
        cuisine = st.selectbox(
            "Cuisine",
            options=["(any)"] + cuisines,
            index=cuisines.index("italian") + 1 if "italian" in cuisines else 0,
        )
        budget = st.radio(
            "Budget (approx cost for two)",
            options=["low", "medium", "high"],
            index=1,
            horizontal=True,
        )
        min_rating = st.slider("Minimum rating", min_value=3.0, max_value=5.0, value=4.0, step=0.1)
        additional = st.text_area(
            "Additional preferences",
            placeholder="e.g. family-friendly, quiet ambience, quick service",
            max_chars=300,
        )
        top_n = st.number_input(
            "Top N",
            min_value=1,
            max_value=20,
            value=int(settings.default_top_n),
            step=1,
        )
        submitted = st.form_submit_button("Get recommendations", type="primary")

    if not submitted:
        return

    loc = None if location == "(any)" else location
    cui = None if cuisine == "(any)" else cuisine
    if not loc and not cui:
        st.error("Select at least a location or a cuisine.")
        return

    try:
        preferences = Preferences(
            location=loc,
            cuisine=cui,
            budget=budget,  # type: ignore[arg-type]
            min_rating=float(min_rating),
            additional_preferences=additional or None,
            top_n=int(top_n),
        )
    except ValidationError as exc:
        st.error(f"Invalid preferences: {exc}")
        return

    with st.spinner("Finding restaurants and ranking with the LLM…"):
        try:
            # Clear settings cache so .env edits during a session are picked up.
            get_settings.cache_clear()
            result = recommend(preferences, settings=get_settings())
        except Exception as exc:  # noqa: BLE001
            st.error(f"Recommendation failed: {exc}")
            return

    _render_results(result)


if __name__ == "__main__":
    main()
