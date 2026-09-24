"""KAIRO V1 context layer."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Context:
    current_input: str
    history: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


class KairoContext:
    """Maintains the active interaction context."""

    def __init__(self, max_history: int = 20) -> None:
        self.max_history = max_history
        self.history: list[str] = []

    def build(self, message: str, metadata: dict | None = None) -> Context:
        message = message.strip()

        if not message:
            raise ValueError("Context input is required.")

        self.history.append(message)
        self.history = self.history[-self.max_history:]

        return Context(
            current_input=message,
            history=list(self.history),
            metadata=metadata or {},
        )

    def clear(self) -> None:
        self.history.clear()

    def snapshot(self) -> dict:
        return {
            "history": list(self.history),
            "history_count": len(self.history),
            "max_history": self.max_history,
        }
