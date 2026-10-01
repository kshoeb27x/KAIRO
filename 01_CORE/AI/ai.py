"""KAIRO V1 AI abstraction layer."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from typing import Any


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

    def __init__(
        self,
        provider: AIProvider | None = None,
        security: Any | None = None,
    ) -> None:
        self.provider = provider
        self.security = security

    def generate(self, prompt: str, context: Any | None = None) -> AIResponse:
        prompt = prompt.strip()

        if not prompt:
            raise ValueError("AI prompt is required.")

        if self.provider is None:
            raise RuntimeError(
                "No AI provider is configured; model generation is unavailable."
            )

        if self.security is None or context is None:
            if self.security is not None:
                self.security.audit.record(
                    "AUTHORIZATION",
                    (
                        context.caller_identity
                        if context is not None
                        else None
                    ),
                    "model.generate",
                    "DENY",
                    {
                        "permission": "model.external",
                        "resource": "configured-provider",
                        "correlation_id": (
                            context.correlation_id
                            if context is not None
                            else None
                        ),
                        "reason": "MISSING_CONTEXT",
                    },
                )
            raise PermissionError(
                "External model access requires an authorization context."
            )
        model_context = context.derive(
            permission="model.external",
            operation="model.generate",
            resource="configured-provider",
            requested_capability="model.external",
        )
        decision = self.security.authorize_context(
            model_context,
            "model.external",
        )
        if not decision.allowed:
            self.security.audit_execution(
                model_context,
                decision.decision,
                decision.reason,
            )
            raise PermissionError(
                f"External model access denied: {decision.reason}"
            )
        try:
            response = self.provider.generate(prompt)
            self.security.audit_execution(model_context, "COMPLETED")
            return response
        except Exception as error:
            self.security.audit_execution(
                model_context,
                "FAILED",
                str(error),
            )
            raise

    def status(self) -> dict:
        return {
            "layer": "AI",
            "status": (
                "READY"
                if self.provider is not None
                else "OFFLINE"
            ),
            "provider": (
                "configured"
                if self.provider is not None
                else "unconfigured"
            ),
        }
