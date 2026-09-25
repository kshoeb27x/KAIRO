from __future__ import annotations

from typing import Any

from .tool import ToolDefinition


class ToolRegistry:
    """Central registry for KAIRO tools."""

    def __init__(self) -> None:
        self._tools: dict[str, Any] = {}

    def register(self, tool: Any) -> None:
        definition = getattr(
            tool,
            "definition",
            None,
        )

        if definition is None:
            raise ValueError(
                "Tool must expose a definition"
            )

        name = definition.name

        if not name:
            raise ValueError(
                "Tool name is required"
            )

        self._tools[name] = tool

    def unregister(
        self,
        name: str,
    ) -> bool:
        return (
            self._tools.pop(
                name,
                None,
            )
            is not None
        )

    def get(
        self,
        name: str,
    ) -> Any | None:
        return self._tools.get(name)

    def definitions(
        self,
    ) -> list[ToolDefinition]:
        return [
            tool.definition
            for tool in self._tools.values()
        ]

    def list_tools(self) -> list[str]:
        return sorted(
            self._tools
        )

    def health(self) -> dict:
        definitions = self.definitions()
        providers = {}
        for name, tool in self._tools.items():
            health = getattr(tool, "provider_health", None)
            if callable(health):
                providers[name] = health()

        return {
            "status": "ONLINE",
            "count": len(definitions),
            "enabled": sum(
                1
                for definition in definitions
                if definition.enabled
            ),
            "providers": providers,
        }
