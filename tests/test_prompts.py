"""Prompt builder smoke tests."""

from __future__ import annotations

import json

from zomato_rec.llm.prompts import SYSTEM_PROMPT, build_messages
from zomato_rec.models import Preferences, RestaurantCandidate


def test_build_messages_contains_candidates_and_top_n():
    prefs = Preferences(
        location="Banashankari",
        cuisine="Italian",
        budget="medium",
        additional_preferences="family-friendly",
        top_n=3,
    )
    candidates = [
        RestaurantCandidate(id=1, name="A", cuisines="italian", location="Banashankari"),
        RestaurantCandidate(id=2, name="B", cuisines="italian", location="Banashankari"),
    ]
    messages = build_messages(prefs, candidates, limited_options=True)
    assert messages[0]["role"] == "system"
    assert "ONLY" in SYSTEM_PROMPT or "only" in SYSTEM_PROMPT.lower()
    user = json.loads(messages[1]["content"])
    assert user["constraints"]["return_count"] == 2  # min(top_n, len(candidates))
    assert len(user["candidates"]) == 2
    assert user["preferences"]["additional_preferences"] == "family-friendly"
