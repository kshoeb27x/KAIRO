from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


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
