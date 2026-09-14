"""Provider-agnostic LLM client adapters."""

from __future__ import annotations

import logging
import time
from typing import Protocol, runtime_checkable

from zomato_rec.config import Settings, get_settings

logger = logging.getLogger(__name__)


class LLMError(RuntimeError):
    """Raised when an LLM call fails after retries."""


@runtime_checkable
class LLMClient(Protocol):
    def complete(self, messages: list[dict], *, temperature: float = 0.2) -> str: ...


class OpenAIClient:
    """OpenAI Chat Completions API (also used for local Ollama OpenAI-compatible)."""

    def __init__(
        self,
        *,
        api_key: str | None,
        model: str,
        base_url: str | None = None,
        timeout: float = 30.0,
        max_retries: int = 1,
    ) -> None:
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover
            raise LLMError("openai package is not installed") from exc

        self._model = model
        self._timeout = timeout
        self._max_retries = max_retries
        kwargs: dict = {"api_key": api_key or "ollama", "timeout": timeout}
        if base_url:
            kwargs["base_url"] = base_url
        self._client = OpenAI(**kwargs)

    def complete(self, messages: list[dict], *, temperature: float = 0.2) -> str:
        last_error: Exception | None = None
        attempts = self._max_retries + 1
        for attempt in range(attempts):
            try:
                response = self._client.chat.completions.create(
                    model=self._model,
                    messages=messages,
                    temperature=temperature,
                )
                content = response.choices[0].message.content
                if not content or not str(content).strip():
                    raise LLMError("Empty LLM response")
                return str(content)
            except Exception as exc:  # noqa: BLE001 — normalized to LLMError
                last_error = exc
                logger.warning(
                    "LLM attempt %s/%s failed: %s", attempt + 1, attempts, exc
                )
                if attempt + 1 < attempts:
                    time.sleep(0.5 * (attempt + 1))
        raise LLMError(f"LLM call failed: {last_error}") from last_error


class GeminiClient:
    """Google Gemini generative language API."""

    def __init__(
        self,
        *,
        api_key: str | None,
        model: str,
        timeout: float = 30.0,
        max_retries: int = 1,
    ) -> None:
        if not api_key:
            raise LLMError("LLM_API_KEY is required for Gemini")
        try:
            import google.generativeai as genai
        except ImportError as exc:  # pragma: no cover
            raise LLMError(
                "google-generativeai is not installed; pip install 'zomato-rec[gemini]'"
            ) from exc

        genai.configure(api_key=api_key)
        self._model = genai.GenerativeModel(model)
        self._timeout = timeout
        self._max_retries = max_retries
        self._genai = genai

    def complete(self, messages: list[dict], *, temperature: float = 0.2) -> str:
        system_parts = [m["content"] for m in messages if m.get("role") == "system"]
        user_parts = [m["content"] for m in messages if m.get("role") != "system"]
        prompt = "\n\n".join(system_parts + user_parts)

        last_error: Exception | None = None
        attempts = self._max_retries + 1
        for attempt in range(attempts):
            try:
                response = self._model.generate_content(
                    prompt,
                    generation_config={"temperature": temperature},
                    request_options={"timeout": self._timeout},
                )
                text = getattr(response, "text", None)
                if not text or not str(text).strip():
                    raise LLMError("Empty LLM response")
                return str(text)
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                logger.warning(
                    "Gemini attempt %s/%s failed: %s", attempt + 1, attempts, exc
                )
                if attempt + 1 < attempts:
                    time.sleep(0.5 * (attempt + 1))
        raise LLMError(f"LLM call failed: {last_error}") from last_error


GROQ_BASE_URL = "https://api.groq.com/openai/v1"


def get_llm_client(settings: Settings | None = None) -> LLMClient | None:
    """Return an LLM client, or ``None`` when credentials are missing."""
    settings = settings or get_settings()
    provider = settings.llm_provider.lower()

    if provider == "groq":
        if not settings.llm_api_key:
            logger.info("No LLM_API_KEY — Groq client unavailable")
            return None
        return OpenAIClient(
            api_key=settings.llm_api_key,
            model=settings.llm_model,
            base_url=GROQ_BASE_URL,
        )

    if provider == "openai":
        if not settings.llm_api_key:
            logger.info("No LLM_API_KEY — OpenAI client unavailable")
            return None
        return OpenAIClient(api_key=settings.llm_api_key, model=settings.llm_model)

    if provider == "ollama":
        return OpenAIClient(
            api_key=settings.llm_api_key or "ollama",
            model=settings.llm_model,
            base_url="http://127.0.0.1:11434/v1",
        )

    if provider == "gemini":
        if not settings.llm_api_key:
            logger.info("No LLM_API_KEY — Gemini client unavailable")
            return None
        return GeminiClient(api_key=settings.llm_api_key, model=settings.llm_model)

    raise LLMError(f"Unsupported LLM_PROVIDER: {settings.llm_provider}")
