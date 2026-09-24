"""KAIRO V1 AI abstraction layer."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class AIResponse:
    content: str
    model: str
    provider: str


class AIProvider(Protocol):
    def generate(self, prompt: str) -> AIResponse:
        ...


class KairoAI:
    """Provider-independent AI interface for KAIRO V1."""

    def __init__(self, provider: AIProvider | None = None) -> None:
        self.provider = provider

    def generate(self, prompt: str) -> AIResponse:
        prompt = prompt.strip()

        if not prompt:
            raise ValueError("AI prompt is required.")

        if self.provider is None:
            return AIResponse(
                content=f"[AI V1] Received: {prompt}",
                model="development",
                provider="kairo",
            )

        return self.provider.generate(prompt)

    def status(self) -> dict:
        return {
            "layer": "AI",
            "status": "READY",
            "provider": (
                "configured"
                if self.provider is not None
                else "development"
            ),
        }
