from __future__ import annotations

from typing import Any

from .tool import ToolRequest, ToolResult


class ToolExecutor:
    """Executes tools through one controlled boundary."""

    def __init__(self, registry: Any) -> None:
        self.registry = registry

    def execute(
        self,
        request: ToolRequest,
    ) -> ToolResult:

        tool = self.registry.get(
            request.tool
        )

        if tool is None:
            return ToolResult(
                tool=request.tool,
                action=request.action,
                status="FAILED",
                result=None,
                error="Tool not registered",
            )

        definition = tool.definition

        if not definition.enabled:
            return ToolResult(
                tool=request.tool,
                action=request.action,
                status="FAILED",
                result=None,
                error="Tool disabled",
            )

        try:
            result = tool.execute(
                request.action,
                request.arguments,
            )

            return ToolResult(
                tool=request.tool,
                action=request.action,
                status="COMPLETED",
                result=result,
            )

        except Exception as exc:
            return ToolResult(
                tool=request.tool,
                action=request.action,
                status="FAILED",
                result=None,
                error=str(exc),
            )
