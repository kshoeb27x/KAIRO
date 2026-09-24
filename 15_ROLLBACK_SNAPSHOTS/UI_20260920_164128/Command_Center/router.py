from __future__ import annotations

from typing import Any, Callable


class CommandRouter:

    def __init__(self) -> None:
        self._handlers: dict[
            str,
            Callable[..., Any],
        ] = {}


    def register(
        self,
        command: str,
        handler: Callable[..., Any],
    ) -> None:

        name = command.strip().lower()

        if not name:
            raise ValueError(
                "Command cannot be empty"
            )

        self._handlers[name] = handler


    def unregister(
        self,
        command: str,
    ) -> bool:

        name = command.strip().lower()

        return (
            self._handlers.pop(
                name,
                None,
            )
            is not None
        )


    def commands(self) -> list[str]:
        return sorted(
            self._handlers.keys()
        )


    def dispatch(
        self,
        command: str,
        **kwargs: Any,
    ) -> Any:

        name = command.strip().lower()

        handler = self._handlers.get(name)

        if handler is None:
            raise KeyError(
                f"Unknown command: {command}"
            )

        return handler(**kwargs)


    def health(self) -> dict[str, Any]:
        return {
            "status": "ONLINE",
            "count": len(
                self._handlers
            ),
            "commands": self.commands(),
        }
