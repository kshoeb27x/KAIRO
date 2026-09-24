from __future__ import annotations

from typing import Any

from .router import CommandRouter


class CommandCenter:

    VERSION = "V1"

    def __init__(
        self,
        core: Any | None = None,
        security: Any | None = None,
    ) -> None:

        self.core = core
        self.security = security

        self.router = CommandRouter()

        self._register_commands()

    def _register_commands(self) -> None:

        self.router.register(
            "status",
            self.status,
            "Return complete KAIRO status.",
            "system.status",
        )

        self.router.register(
            "health",
            self.health,
            "Return KAIRO health.",
            "system.health",
        )

        self.router.register(
            "agents",
            self.agents,
            "List registered agents.",
            "agents.read",
        )

        self.router.register(
            "events",
            self.events,
            "Return runtime events.",
            "events.read",
        )

        self.router.register(
            "task",
            self.create_task,
            "Create runtime task.",
            "tasks.create",
        )

        self.router.register(
            "chat",
            self.chat,
            "Send message through KAIRO.",
            "core.chat",
        )

    def _authorize(
        self,
        identity_id: str | None,
        permission: str | None,
    ) -> bool:

        if self.security is None:
            return True

        if permission is None:
            return True

        if not identity_id:
            return False

        result = self.security.authorize(
            identity_id=identity_id,
            permission=permission,
        )

        if isinstance(result, bool):
            return result

        if isinstance(result, dict):
            return bool(
                result.get("allowed")
            )

        return bool(
            getattr(
                result,
                "allowed",
                False,
            )
        )

    def execute(
        self,
        command: str,
        identity_id: str | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> Any:

        definition = self.router.get(
            command
        )

        if not self._authorize(
            identity_id,
            definition.permission,
        ):
            return {
                "status": "DENIED",
                "command": command,
                "reason": "Authorization failed",
            }

        return self.router.dispatch(
            command,
            *args,
            **kwargs,
        )

    def status(
        self,
        identity_id: str | None = None,
    ) -> dict[str, Any]:

        if self.core is None:
            return {
                "system": "KAIRO",
                "version": self.VERSION,
                "status": "ONLINE",
                "core": None,
            }

        if hasattr(
            self.core,
            "status",
        ):
            result = self.core.status()

            if isinstance(
                result,
                dict,
            ):
                return result

        return {
            "system": "KAIRO",
            "version": self.VERSION,
            "status": "ONLINE",
        }

    def health(
        self,
        identity_id: str | None = None,
    ) -> dict[str, Any]:

        if self.core is None:
            return {
                "system": "KAIRO",
                "version": self.VERSION,
                "status": "ONLINE",
            }

        if hasattr(
            self.core,
            "health",
        ):
            result = self.core.health()

            if isinstance(
                result,
                dict,
            ):
                return result

        return {
            "system": "KAIRO",
            "version": self.VERSION,
            "status": "ONLINE",
        }

    def agents(
        self,
        identity_id: str | None = None,
    ) -> list[str]:

        if self.core is None:
            return []

        if hasattr(
            self.core,
            "list_agents",
        ):
            return list(
                self.core.list_agents()
            )

        return []

    def events(
        self,
        limit: int = 50,
        identity_id: str | None = None,
    ) -> list[dict[str, Any]]:

        if self.core is None:
            return []

        if hasattr(
            self.core,
            "events",
        ):
            return list(
                self.core.events(limit)
            )

        if hasattr(
            self.core,
            "runtime",
        ):
            runtime = self.core.runtime

            if hasattr(
                runtime,
                "recent_events",
            ):
                return list(
                    runtime.recent_events(
                        limit
                    )
                )

        return []

    def create_task(
        self,
        name: str,
        identity_id: str | None = None,
    ) -> dict[str, Any]:

        if not name:
            raise ValueError(
                "Task name cannot be empty"
            )

        if self.core is None:
            return {
                "status": "CREATED",
                "name": name,
            }

        if hasattr(
            self.core,
            "create_task",
        ):
            return self.core.create_task(
                name
            )

        if hasattr(
            self.core,
            "runtime",
        ):
            runtime = self.core.runtime

            if hasattr(
                runtime,
                "create_task",
            ):
                return runtime.create_task(
                    name
                )

        return {
            "status": "CREATED",
            "name": name,
        }

    def chat(
        self,
        message: str,
        identity_id: str | None = None,
    ) -> str:

        if not message:
            raise ValueError(
                "Message cannot be empty"
            )

        if self.core is None:
            return message

        if hasattr(
            self.core,
            "respond",
        ):
            return str(
                self.core.respond(message)
            )

        return message

    def command_list(
        self,
    ) -> list[dict[str, Any]]:

        return self.router.definitions()

    def health_router(
        self,
    ) -> dict[str, Any]:

        return self.router.health()
