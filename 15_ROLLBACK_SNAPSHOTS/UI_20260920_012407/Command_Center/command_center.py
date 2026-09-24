from __future__ import annotations

from typing import Any

from .router import CommandRouter


class CommandCenter:

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
        )

        self.router.register(
            "health",
            self.health,
        )

        self.router.register(
            "agents",
            self.agents,
        )

        self.router.register(
            "events",
            self.events,
        )

        self.router.register(
            "task",
            self.create_task,
        )

        self.router.register(
            "chat",
            self.chat,
        )


    def _authorize(
        self,
        identity_id: str | None,
        permission: str,
    ) -> bool:

        if self.security is None:
            return True

        if not identity_id:
            return False

        try:
            result = self.security.authorize(
                identity_id,
                permission,
            )

            if isinstance(
                result,
                dict,
            ):
                return bool(
                    result.get(
                        "allowed",
                        False,
                    )
                )

            return bool(result)

        except Exception:
            return False


    def status(
        self,
        identity_id: str | None = None,
    ) -> dict[str, Any]:

        if not self._authorize(
            identity_id,
            "ui.status",
        ):
            return {
                "status": "DENIED",
                "reason": "Unauthorized",
            }

        if self.core is None:
            return {
                "status": "ONLINE",
                "core": "UNAVAILABLE",
            }

        if hasattr(
            self.core,
            "status",
        ):
            return self.core.status()

        return {
            "status": "ONLINE",
        }


    def health(
        self,
        identity_id: str | None = None,
    ) -> dict[str, Any]:

        if not self._authorize(
            identity_id,
            "ui.health",
        ):
            return {
                "status": "DENIED",
                "reason": "Unauthorized",
            }

        if self.core is None:
            return {
                "status": "ONLINE",
                "core": "UNAVAILABLE",
            }

        if hasattr(
            self.core,
            "health",
        ):
            return self.core.health()

        return {
            "status": "ONLINE",
        }


    def agents(
        self,
        identity_id: str | None = None,
    ) -> dict[str, Any]:

        if not self._authorize(
            identity_id,
            "ui.agents",
        ):
            return {
                "status": "DENIED",
                "reason": "Unauthorized",
            }

        if self.core is None:
            return {
                "status": "ONLINE",
                "agents": [],
                "count": 0,
            }

        if hasattr(
            self.core,
            "list_agents",
        ):
            agents = self.core.list_agents()
        else:
            agents = []

        return {
            "status": "ONLINE",
            "agents": agents,
            "count": len(agents),
        }


    def events(
        self,
        identity_id: str | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:

        if not self._authorize(
            identity_id,
            "ui.events",
        ):
            return {
                "status": "DENIED",
                "reason": "Unauthorized",
            }

        if self.core is None:
            return {
                "status": "ONLINE",
                "events": [],
                "count": 0,
            }

        if not hasattr(
            self.core,
            "events",
        ):
            return {
                "status": "ONLINE",
                "events": [],
                "count": 0,
            }

        events = self.core.events(
            limit
        )

        return {
            "status": "ONLINE",
            "events": events,
            "count": len(events),
        }


    def create_task(
        self,
        name: str,
        identity_id: str | None = None,
    ) -> dict[str, Any]:

        if not self._authorize(
            identity_id,
            "ui.task.create",
        ):
            return {
                "status": "DENIED",
                "reason": "Unauthorized",
            }

        if self.core is None:
            return {
                "status": "FAILED",
                "reason": "Core unavailable",
            }

        if not hasattr(
            self.core,
            "create_task",
        ):
            return {
                "status": "FAILED",
                "reason": (
                    "Task interface unavailable"
                ),
            }

        task = self.core.create_task(
            name
        )

        return {
            "status": "CREATED",
            "task": task,
        }


    def chat(
        self,
        message: str,
        identity_id: str | None = None,
    ) -> dict[str, Any]:

        if not self._authorize(
            identity_id,
            "ui.chat",
        ):
            return {
                "status": "DENIED",
                "reason": "Unauthorized",
            }

        if self.core is None:
            return {
                "status": "FAILED",
                "reason": "Core unavailable",
            }

        if not hasattr(
            self.core,
            "respond",
        ):
            return {
                "status": "FAILED",
                "reason": (
                    "Response interface unavailable"
                ),
            }

        response = self.core.respond(
            message
        )

        return {
            "status": "COMPLETED",
            "response": response,
        }


    def execute(
        self,
        command: str,
        identity_id: str | None = None,
        **kwargs: Any,
    ) -> Any:

        return self.router.dispatch(
            command,
            identity_id=identity_id,
            **kwargs,
        )


    def health(self) -> dict[str, Any]:

        return {
            "status": "ONLINE",
            "router": self.router.health(),
            "core_connected": (
                self.core is not None
            ),
            "security_connected": (
                self.security is not None
            ),
        }
