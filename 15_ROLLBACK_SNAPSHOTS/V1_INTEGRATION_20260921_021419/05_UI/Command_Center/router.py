from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


CommandHandler = Callable[..., Any]


@dataclass
class CommandDefinition:
    name: str
    handler: CommandHandler
    description: str
    permission: str | None = None


class CommandRouter:

    def __init__(self) -> None:
        self._commands: dict[str, CommandDefinition] = {}

    def register(
        self,
        name: str,
        handler: CommandHandler,
        description: str = "",
        permission: str | None = None,
    ) -> None:

        if not name:
            raise ValueError(
                "Command name cannot be empty"
            )

        self._commands[name] = CommandDefinition(
            name=name,
            handler=handler,
            description=description,
            permission=permission,
        )

    def unregister(self, name: str) -> bool:
        return (
            self._commands.pop(
                name,
                None,
            )
            is not None
        )

    def commands(self) -> list[str]:
        return sorted(
            self._commands
        )

    def definitions(self) -> list[dict[str, Any]]:
        return [
            {
                "name": definition.name,
                "description": definition.description,
                "permission": definition.permission,
            }
            for definition in self._commands.values()
        ]

    def get(
        self,
        name: str,
    ) -> CommandDefinition:

        definition = self._commands.get(name)

        if definition is None:
            raise KeyError(
                f"Unknown command: {name}"
            )

        return definition

    def dispatch(
        self,
        name: str,
        *args: Any,
        **kwargs: Any,
    ) -> Any:

        definition = self.get(name)

        return definition.handler(
            *args,
            **kwargs,
        )

    def health(self) -> dict[str, Any]:
        return {
            "router": "ONLINE",
            "commands": len(
                self._commands
            ),
            "registered": self.commands(),
        }
