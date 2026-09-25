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

    def execute(
        self,
        action: str,
        arguments: dict[str, Any],
    ) -> Any:

        if action == "health":
            return {
                "status": "ONLINE",
                "category": "Browser",
            }

        if action == "describe":
            return {
                "name": self.definition.name,
                "category": self.definition.category,
                "description": self.definition.description,
                "permissions": list(
                    self.definition.permissions
                ),
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
