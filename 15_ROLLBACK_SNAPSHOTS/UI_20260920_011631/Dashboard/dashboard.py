from __future__ import annotations

from typing import Any


class Dashboard:
    """Aggregates operational data for KAIRO."""

    def __init__(self, command_center: Any) -> None:
        self.command_center = command_center

    def overview(
        self,
        identity_id: str | None = None,
    ) -> dict[str, Any]:

        status = self.command_center.status(
            identity_id=identity_id,
        )

        health = self.command_center.health()

        agents = self.command_center.agents(
            identity_id=identity_id,
        )

        events = self.command_center.events(
            identity_id=identity_id,
            limit=20,
        )

        return {
            "status": status,
            "health": health,
            "agents": agents,
            "events": events,
        }

    def summary(
        self,
        identity_id: str | None = None,
    ) -> dict[str, Any]:

        overview = self.overview(
            identity_id=identity_id,
        )

        status = overview["status"]

        return {
            "system": status.get("system"),
            "core": status.get("core"),
            "mode": status.get("mode"),
            "agent_count": overview["agents"].get(
                "count",
                0,
            ),
            "event_count": overview["events"].get(
                "count",
                0,
            ),
        }

    def health(self) -> dict[str, Any]:
        return {
            "status": "ONLINE",
            "command_center": self.command_center.health(),
        }
