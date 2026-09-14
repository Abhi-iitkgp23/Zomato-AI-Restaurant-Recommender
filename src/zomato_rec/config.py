"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

# Zomato-M7/ (repo root)
PROJECT_ROOT = Path(__file__).resolve().parents[2]

load_dotenv(PROJECT_ROOT / ".env")


def _env(key: str, default: str | None = None) -> str | None:
    value = os.getenv(key, default)
    if value is None:
        return None
    value = value.strip()
    return value if value else None


def _env_int(key: str, default: int) -> int:
    raw = _env(key)
    if raw is None:
        return default
    return int(raw)


def _resolve_path(raw: str | None, default_relative: str) -> Path:
    path = Path(raw) if raw else PROJECT_ROOT / default_relative
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path.resolve()


@dataclass(frozen=True)
class Settings:
    """Runtime settings for data paths, LLM, and filter thresholds."""

    llm_provider: str
    llm_api_key: str | None
    llm_model: str
    data_path: Path
    metadata_path: Path
    candidate_k: int
    default_top_n: int
    budget_low_max: int
    budget_med_max: int
    hf_dataset_id: str
    hf_dataset_revision: str | None
    project_root: Path = PROJECT_ROOT

    @property
    def has_llm_credentials(self) -> bool:
        provider = self.llm_provider.lower()
        if provider == "ollama":
            return True
        return bool(self.llm_api_key)

    def validate(self) -> None:
        """Raise ValueError for unsafe or inconsistent configuration."""
        allowed = {"groq", "openai", "gemini", "ollama"}
        if self.llm_provider.lower() not in allowed:
            raise ValueError(
                f"Unknown LLM_PROVIDER={self.llm_provider!r}; "
                f"expected one of {sorted(allowed)}"
            )
        if self.candidate_k < 1:
            raise ValueError("CANDIDATE_K must be >= 1")
        if self.candidate_k > 20:
            raise ValueError("CANDIDATE_K must be <= 20 (token/cost guardrail)")
        if self.default_top_n < 1:
            raise ValueError("DEFAULT_TOP_N must be >= 1")
        if self.budget_low_max < 0 or self.budget_med_max < 0:
            raise ValueError("Budget thresholds must be non-negative")
        if self.budget_low_max >= self.budget_med_max:
            raise ValueError(
                "BUDGET_LOW_MAX must be < BUDGET_MED_MAX "
                f"(got {self.budget_low_max} >= {self.budget_med_max})"
            )


@lru_cache(maxsize=1)
def get_settings(*, validate: bool = True) -> Settings:
    """Load settings once from the environment."""
    candidate_k = _env_int("CANDIDATE_K", 15)
    # Soft-cap oversized values to the architecture guardrail when not validating.
    if not validate and candidate_k > 20:
        candidate_k = 20
    if not validate and candidate_k < 1:
        candidate_k = 1

    settings = Settings(
        llm_provider=(_env("LLM_PROVIDER", "groq") or "groq").lower(),
        llm_api_key=_env("LLM_API_KEY"),
        llm_model=_env("LLM_MODEL", "openai/gpt-oss-120b")
        or "openai/gpt-oss-120b",
        data_path=_resolve_path(_env("DATA_PATH"), "data/processed/restaurants.parquet"),
        metadata_path=_resolve_path(
            _env("METADATA_PATH"), "data/processed/metadata.json"
        ),
        candidate_k=candidate_k,
        default_top_n=_env_int("DEFAULT_TOP_N", 5),
        budget_low_max=_env_int("BUDGET_LOW_MAX", 400),
        budget_med_max=_env_int("BUDGET_MED_MAX", 800),
        hf_dataset_id=_env("HF_DATASET_ID", "ManikaSaini/zomato-restaurant-recommendation")
        or "ManikaSaini/zomato-restaurant-recommendation",
        hf_dataset_revision=_env("HF_DATASET_REVISION"),
    )
    if validate:
        settings.validate()
    return settings


# Module-level convenience aliases (recomputed via get_settings).
def __getattr__(name: str):
    settings = get_settings(validate=False)
    mapping = {
        "LLM_PROVIDER": settings.llm_provider,
        "LLM_API_KEY": settings.llm_api_key,
        "LLM_MODEL": settings.llm_model,
        "DATA_PATH": settings.data_path,
        "METADATA_PATH": settings.metadata_path,
        "CANDIDATE_K": settings.candidate_k,
        "DEFAULT_TOP_N": settings.default_top_n,
        "BUDGET_LOW_MAX": settings.budget_low_max,
        "BUDGET_MED_MAX": settings.budget_med_max,
        "HF_DATASET_ID": settings.hf_dataset_id,
        "HF_DATASET_REVISION": settings.hf_dataset_revision,
    }
    if name in mapping:
        return mapping[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
