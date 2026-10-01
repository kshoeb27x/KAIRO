from __future__ import annotations

from dataclasses import dataclass, field
from importlib import import_module
from typing import Any, Protocol

ExecutionContext = import_module(
    "06_SECURITY.execution_context"
).ExecutionContext


@dataclass
class ToolDefinition:
    name: str
    description: str
    category: str
    permissions: list[str] = field(default_factory=list)
    enabled: bool = True
    metadata: dict[str, Any] = field(
        default_factory=dict
    )


@dataclass
class ToolRequest:
    tool: str
    action: str
    arguments: dict[str, Any] = field(
        default_factory=dict
    )
    context: Any | None = None


@dataclass
class ToolResult:
    tool: str
    action: str
    status: str
    result: Any
    error: str | None = None


class Tool(Protocol):
    definition: ToolDefinition

    def execute(
        self,
        action: str,
        arguments: dict[str, Any],
    ) -> Any:
        ...
