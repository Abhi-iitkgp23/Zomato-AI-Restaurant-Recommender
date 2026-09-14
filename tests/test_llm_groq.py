"""Groq provider wiring tests."""

from __future__ import annotations

from zomato_rec.config import get_settings
from zomato_rec.llm.client import GROQ_BASE_URL, OpenAIClient, get_llm_client


def test_groq_allowed_in_settings(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.setenv("LLM_MODEL", "openai/gpt-oss-120b")
    monkeypatch.setenv("LLM_API_KEY", "gsk-test")
    get_settings.cache_clear()
    settings = get_settings()
    assert settings.llm_provider == "groq"
    assert settings.has_llm_credentials is True


def test_get_llm_client_groq_uses_base_url(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.setenv("LLM_API_KEY", "gsk-test")
    monkeypatch.setenv("LLM_MODEL", "openai/gpt-oss-120b")
    get_settings.cache_clear()
    client = get_llm_client()
    assert isinstance(client, OpenAIClient)
    # OpenAI SDK stores base_url on the client
    assert str(client._client.base_url).rstrip("/") == GROQ_BASE_URL.rstrip("/")


def test_get_llm_client_groq_without_key_returns_none(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    get_settings.cache_clear()
    assert get_llm_client() is None
