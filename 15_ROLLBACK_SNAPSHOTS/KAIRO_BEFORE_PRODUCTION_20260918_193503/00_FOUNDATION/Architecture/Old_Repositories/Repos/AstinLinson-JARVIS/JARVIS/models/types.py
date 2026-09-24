"""Typed data structures shared across JARVIS modules."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal


Role = Literal["system", "user", "assistant", "tool"]


@dataclass(frozen=True, slots=True)
class Message:
    """A single conversational message exchanged with the AI brain."""

    role: Role
    content: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class SkillResult:
    """Result returned by a skill after it handles a command."""

    content: str
    handled: bool = True
