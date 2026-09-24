"""Language model provider implementations."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from time import perf_counter
from typing import Any

from JARVIS.config.settings import LLMSettings
from JARVIS.models.exceptions import InvalidConfigurationError, LLMTimeoutError
from JARVIS.models.interfaces import LanguageModel
from JARVIS.models.types import Message


class EchoLanguageModel(LanguageModel):
    """Local development model that proves the brain pipeline without an API."""

    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger

    def generate(
        self,
        messages: Sequence[Message],
        *,
        timeout_seconds: float | None = None,
    ) -> str:
        """Return a deterministic response based on the latest user message."""

        del timeout_seconds
        latest_user_message = next(
            (message.content for message in reversed(messages) if message.role == "user"),
            "",
        )
        self._logger.info("Echo language model generated a response.")
        return (
            "I heard you say: "
            f"{latest_user_message}. "
            "The v0.1 brain pipeline is online."
        )


class OpenAICompatibleLanguageModel(LanguageModel):
    """Cloud model adapter using an OpenAI-compatible chat completions API."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        api_base_url: str | None,
        logger: logging.Logger,
    ) -> None:
        if not api_key:
            raise InvalidConfigurationError("An API key is required for the OpenAI-compatible LLM.")

        self._api_key = api_key
        self._model = model
        self._api_base_url = api_base_url
        self._logger = logger
        self._client: Any | None = None

    def generate(
        self,
        messages: Sequence[Message],
        *,
        timeout_seconds: float | None = None,
    ) -> str:
        """Generate a response with the configured cloud model."""

        start_time = perf_counter()
        try:
            response = self._get_client().chat.completions.create(
                model=self._model,
                messages=[
                    {"role": message.role, "content": message.content}
                    for message in messages
                    if message.role in {"system", "user", "assistant", "tool"}
                ],
                timeout=timeout_seconds,
            )
        except TimeoutError as exc:
            raise LLMTimeoutError("Language model request timed out.") from exc
        except Exception as exc:
            if exc.__class__.__name__.lower().endswith("timeout"):
                raise LLMTimeoutError("Language model request timed out.") from exc
            raise

        elapsed = perf_counter() - start_time
        self._logger.info("Cloud language model responded in %.3f seconds.", elapsed)
        content = response.choices[0].message.content
        if not content:
            return "I received an empty response from the language model."

        import re
        content_str = str(content)

        # ── DIAGNOSTIC: log the raw LLM output before any processing ──────────
        self._logger.info("[LLM RAW OUTPUT]\n%s", content_str)
        non_printable = [
            f"U+{ord(c):04X} at index {i}"
            for i, c in enumerate(content_str)
            if not c.isprintable() and c not in ("\n", "\r", "\t")
        ]
        if non_printable:
            self._logger.warning("[LLM RAW OUTPUT] Non-printable chars: %s", non_printable)
        # ──────────────────────────────────────────────────────────────────────

        # Remove reasoning blocks emitted by models like Qwen3 or DeepSeek
        content_str = re.sub(r'<think>.*?</think>', '', content_str, flags=re.DOTALL).strip()

        return content_str

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client

        try:
            from openai import OpenAI
        except ImportError as exc:
            raise InvalidConfigurationError(
                "Install the 'openai' package to use the OpenAI-compatible LLM provider."
            ) from exc

        if self._api_base_url:
            self._client = OpenAI(api_key=self._api_key, base_url=self._api_base_url)
        else:
            self._client = OpenAI(api_key=self._api_key)
        return self._client


def create_language_model(settings: LLMSettings, logger: logging.Logger) -> LanguageModel:
    """Factory for the configured language model provider."""

    provider = settings.provider.strip().lower()
    if provider == "echo":
        return EchoLanguageModel(logger)
    if provider in {"openai", "openai_compatible"}:
        if settings.api_key is None:
            raise InvalidConfigurationError(
                "Set JARVIS_LLM_API_KEY or OPENAI_API_KEY for the configured LLM provider."
            )
        return OpenAICompatibleLanguageModel(
            api_key=settings.api_key,
            model=settings.model,
            api_base_url=settings.api_base_url,
            logger=logger,
        )
    raise InvalidConfigurationError(f"Unsupported LLM provider: {settings.provider}")
