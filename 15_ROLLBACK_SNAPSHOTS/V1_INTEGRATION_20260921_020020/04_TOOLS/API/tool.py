from __future__ import annotations

from typing import Any

from ..tool import ToolDefinition


class APITool:
    """External API integration interface."""

    definition = ToolDefinition(
        name="api",
        description="External API integration interface.",
        category="API",
        permissions=['network.read', 'network.write'],
    )

    def execute(
        self,
        action: str,
        arguments: dict[str, Any],
    ) -> Any:

        if action == "health":
            return {
                "status": "ONLINE",
                "category": "API",
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
