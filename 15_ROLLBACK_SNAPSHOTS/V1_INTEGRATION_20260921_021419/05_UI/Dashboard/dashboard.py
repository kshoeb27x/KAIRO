from __future__ import annotations

from typing import Any


class Dashboard:

    VERSION = "V1"

    def __init__(
        self,
        command_center: Any,
    ) -> None:

        self.command_center = command_center

    def overview(
        self,
    ) -> dict[str, Any]:

        status = self.command_center.execute(
            "status"
        )

        health = self.command_center.execute(
            "health"
        )

        agents = self.command_center.execute(
            "agents"
        )

        events = self.command_center.execute(
            "events",
            limit=20,
        )

        return {
            "system": "KAIRO",
            "version": self.VERSION,
            "status": status,
            "health": health,
            "agents": agents,
            "events": events,
        }

    def summary(
        self,
    ) -> dict[str, Any]:

        status = self.command_center.execute(
            "status"
        )

        health = self.command_center.execute(
            "health"
        )

        agents = self.command_center.execute(
            "agents"
        )

        events = self.command_center.execute(
            "events",
            limit=20,
        )

        return {
            "system": "KAIRO",
            "status": status,
            "health": health,
            "agent_count": len(
                agents
            ),
            "event_count": len(
                events
            ),
        }

    def health(
        self,
    ) -> dict[str, Any]:

        return {
            "dashboard": "ONLINE",
            "version": self.VERSION,
            "command_center": (
                self.command_center.health_router()
            ),
        }
