from __future__ import annotations

from typing import Any

from ..tool import ToolDefinition


class ComputerUseTool:
    """Computer interaction interface."""

    definition = ToolDefinition(
        name="computer_use",
        description="Computer interaction interface.",
        category="Computer_Use",
        permissions=['computer.interact'],
    )

    def execute(
        self,
        action: str,
        arguments: dict[str, Any],
    ) -> Any:

        if action == "health":
            return {
                "status": "ONLINE",
                "category": "Computer_Use",
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
