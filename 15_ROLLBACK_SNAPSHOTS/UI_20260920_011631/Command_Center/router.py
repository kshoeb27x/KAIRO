from __future__ import annotations

from typing import Any, Callable


class CommandRouter:
    """Routes commands to registered handlers."""

    def __init__(self) -> None:
        self._handlers: dict[str, Callable[..., Any]] = {}

    def register(self, command: str, handler: Callable[..., Any]) -> None:
        normalized = command.strip().lower()

        if not normalized:
            raise ValueError("Command cannot be empty")

        self._handlers[normalized] = handler

    def unregister(self, command: str) -> bool:
        return self._handlers.pop(
            command.strip().lower(),
            None,
        ) is not None

    def commands(self) -> list[str]:
        return sorted(self._handlers)

    def dispatch(self, command: str, **kwargs: Any) -> Any:
        normalized = command.strip().lower()

        handler = self._handlers.get(normalized)

        if handler is None:
            raise KeyError(f"Unknown command: {command}")

        return handler(**kwargs)

    def health(self) -> dict[str, Any]:
        return {
            "status": "ONLINE",
            "commands": self.commands(),
            "count": len(self._handlers),
        }
