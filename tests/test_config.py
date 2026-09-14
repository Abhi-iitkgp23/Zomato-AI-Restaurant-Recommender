"""Phase 0: configuration loading and validation."""

from __future__ import annotations

import pytest

from zomato_rec import config
from zomato_rec.config import Settings, get_settings


@pytest.fixture(autouse=True)
def clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_get_settings_defaults(monkeypatch):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("LLM_MODEL", "gpt-4o-mini")
    monkeypatch.setenv("CANDIDATE_K", "15")
    monkeypatch.setenv("DEFAULT_TOP_N", "5")
    monkeypatch.setenv("BUDGET_LOW_MAX", "400")
    monkeypatch.setenv("BUDGET_MED_MAX", "800")

    settings = get_settings()
    assert isinstance(settings, Settings)
    assert settings.llm_provider == "openai"
    assert settings.candidate_k == 15
    assert settings.default_top_n == 5
    assert settings.budget_low_max == 400
    assert settings.budget_med_max == 800
    assert settings.data_path.name == "restaurants.parquet"
    assert settings.project_root.name == "Zomato-M7"


def test_unknown_provider_rejected(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "not-a-provider")
    with pytest.raises(ValueError, match="Unknown LLM_PROVIDER"):
        get_settings(validate=True)


def test_inverted_budget_thresholds_rejected(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("BUDGET_LOW_MAX", "900")
    monkeypatch.setenv("BUDGET_MED_MAX", "400")
    with pytest.raises(ValueError, match="BUDGET_LOW_MAX"):
        get_settings(validate=True)


def test_candidate_k_upper_bound(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("CANDIDATE_K", "25")
    with pytest.raises(ValueError, match="CANDIDATE_K"):
        get_settings(validate=True)


def test_module_level_aliases(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("CANDIDATE_K", "10")
    get_settings.cache_clear()
    assert config.LLM_PROVIDER == "ollama"
    assert config.CANDIDATE_K == 10


def test_has_llm_credentials(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    assert get_settings().has_llm_credentials is False

    get_settings.cache_clear()
    monkeypatch.setenv("LLM_API_KEY", "sk-test")
    assert get_settings().has_llm_credentials is True

    get_settings.cache_clear()
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    assert get_settings().has_llm_credentials is True
