"""Phase 4 safety + observability helpers."""

from __future__ import annotations

from zomato_rec.models import Preferences
from zomato_rec.observability import preference_hash, redact_secrets
from zomato_rec.safety import sanitize_text


def test_sanitize_strips_control_and_truncates():
    dirty = "Hello\x00 world" + ("x" * 100)
    out = sanitize_text(dirty, max_len=20)
    assert "\x00" not in out
    assert out.endswith("…")
    assert len(out) <= 21


def test_sanitize_html_escape():
    assert "&lt;script&gt;" in sanitize_text("<script>alert(1)</script>", escape=True)


def test_preference_hash_stable():
    a = Preferences(location="Banashankari", cuisine="Italian", budget="medium")
    b = Preferences(location="Banashankari", cuisine="Italian", budget="medium")
    assert preference_hash(a) == preference_hash(b)
    c = Preferences(location="Koramangala", cuisine="Italian", budget="medium")
    assert preference_hash(a) != preference_hash(c)


def test_redact_secrets():
    out = redact_secrets({"llm_api_key": "gsk_secret", "model": "x"})
    assert out["llm_api_key"] == "***"
    assert out["model"] == "x"


def test_additional_preferences_truncated_by_model():
    long = "family " * 100
    prefs = Preferences(location="Banashankari", additional_preferences=long)
    assert prefs.additional_preferences is not None
    assert len(prefs.additional_preferences) <= 300
