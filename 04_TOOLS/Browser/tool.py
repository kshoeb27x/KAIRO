from __future__ import annotations

from typing import Any

from ..tool import ToolDefinition
from .provider import BrowserRequest, BrowserProvider


class BrowserTool:
    """Browser interaction interface."""

    definition = ToolDefinition(
        name="browser",
        description="Browser interaction interface.",
        category="Browser",
        permissions=['network.read'],
    )

    def __init__(self, provider: BrowserProvider | None = None) -> None:
        self.provider = provider

    def provider_health(self) -> dict[str, Any]:
        if self.provider is None:
            return {
                "status": "OPTIONAL_PROVIDER_UNAVAILABLE",
                "provider_configured": False,
            }
        return {
            "status": "ONLINE",
            "provider_configured": True,
            "provider": self.provider.health(),
        }

    def execute(
        self,
        action: str,
        arguments: dict[str, Any],
    ) -> Any:

        if action == "health":
            health = {
                "status": (
                    "ONLINE"
                    if self.provider is not None
                    else "OPTIONAL_PROVIDER_UNAVAILABLE"
                ),
                "category": "Browser",
            }
            if self.provider is not None:
                health["provider"] = self.provider.health()
            return health

        if action == "describe":
            return {
                "name": self.definition.name,
                "category": self.definition.category,
                "description": self.definition.description,
                "permissions": list(
                    self.definition.permissions
                ),
                "provider_configured": self.provider is not None,
            }

        if action in {"navigate", "click", "type"}:
            if self.provider is None:
                raise RuntimeError(
                    "No browser provider is configured for external browser automation."
                )
            return self.provider.execute(BrowserRequest(action, arguments))

        if action == "echo":
            return {
                "message": arguments.get(
                    "message",
                    "",
                ),
            }

        raise ValueError(
            f"Unsupported action: {action}"
        )
