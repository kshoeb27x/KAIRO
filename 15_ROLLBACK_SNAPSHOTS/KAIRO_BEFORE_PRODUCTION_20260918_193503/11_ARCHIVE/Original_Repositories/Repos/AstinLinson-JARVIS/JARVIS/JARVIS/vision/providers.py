"""Vision provider abstraction for routing requests to different VLMs."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

from JARVIS.config.settings import VisionSettings
from JARVIS.models.exceptions import InvalidConfigurationError
from JARVIS.vision.prompt import build_vision_prompt


class VisionProvider(ABC):
    """Abstract interface for a Vision Language Model provider."""

    @abstractmethod
    def analyze(self, image_base64: str, ocr_text: str | None, question: str) -> str:
        """Analyze the image and OCR text to answer the user's question."""


class OpenAICompatibleVisionProvider(VisionProvider):
    """Provider for OpenAI-compatible APIs (like Ollama or vLLM)."""

    def __init__(self, settings: VisionSettings, logger: logging.Logger) -> None:
        self._settings = settings
        self._logger = logger
        self._client: Any | None = None

    def analyze(self, image_base64: str, ocr_text: str | None, question: str) -> str:
        client = self._get_client()
        prompt = build_vision_prompt(question, ocr_text)

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}},
                ],
            }
        ]

        self._logger.info("Vision: Sending image to model (%s)...", self._settings.model)
        response = client.chat.completions.create(
            model=self._settings.model,
            messages=messages,
            timeout=self._settings.timeout_seconds,
        )
        self._logger.info("Vision: Response received.")
        
        return str(response.choices[0].message.content)

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client

        try:
            from openai import OpenAI
        except ImportError as exc:
            raise InvalidConfigurationError("Install 'openai' to use VisionProvider.") from exc

        if not self._settings.api_key and not self._settings.api_base_url:
            raise InvalidConfigurationError("VisionProvider requires api_key or api_base_url.")

        if self._settings.api_base_url:
            self._client = OpenAI(
                api_key=self._settings.api_key or "sk-dummy",
                base_url=self._settings.api_base_url,
            )
        else:
            self._client = OpenAI(api_key=self._settings.api_key)

        return self._client


# Future-ready stubs
class OpenAIVisionProvider(OpenAICompatibleVisionProvider):
    """Native OpenAI provider."""
    pass


class AnthropicVisionProvider(VisionProvider):
    """Native Anthropic provider."""
    def analyze(self, image_base64: str, ocr_text: str | None, question: str) -> str:
        raise NotImplementedError("Anthropic provider not yet implemented.")


class GoogleVisionProvider(VisionProvider):
    """Native Google (Gemini) provider."""
    def analyze(self, image_base64: str, ocr_text: str | None, question: str) -> str:
        raise NotImplementedError("Google provider not yet implemented.")


def create_vision_provider(settings: VisionSettings, logger: logging.Logger) -> VisionProvider:
    """Factory for vision providers."""
    provider_name = settings.provider.strip().lower()
    
    if provider_name in {"ollama", "openai_compatible"}:
        return OpenAICompatibleVisionProvider(settings, logger)
    if provider_name == "openai":
        return OpenAIVisionProvider(settings, logger)
    if provider_name == "anthropic":
        return AnthropicVisionProvider(settings, logger)
    if provider_name == "google":
        return GoogleVisionProvider(settings, logger)
        
    raise InvalidConfigurationError(f"Unsupported vision provider: {provider_name}")
