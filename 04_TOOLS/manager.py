from __future__ import annotations

from typing import Any

from .executor import ToolExecutor
from .registry import ToolRegistry
from .tool import ToolRequest


class ToolManager:
    """Unified management interface for KAIRO tools."""

    def __init__(self, security: Any | None = None) -> None:
        self.registry = ToolRegistry()
        self.security = security
        self.executor = ToolExecutor(
            self.registry,
            security,
        )

    def register(self, tool: Any) -> None:
        self.registry.register(tool)

    def unregister(
        self,
        name: str,
    ) -> bool:
        return self.registry.unregister(
            name
        )

    def get(
        self,
        name: str,
    ) -> Any | None:
        return self.registry.get(name)

    def list_tools(self) -> list[str]:
        return self.registry.list_tools()

    def execute(
        self,
        tool: str,
        action: str,
        arguments: dict | None = None,
        context: Any | None = None,
    ):
        request = ToolRequest(
            tool=tool,
            action=action,
            arguments=arguments or {},
            context=context,
        )

        return self.executor.execute(
            request,
            context,
        )

    def health(self) -> dict:
        return self.registry.health()
