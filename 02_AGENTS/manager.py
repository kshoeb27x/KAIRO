from __future__ import annotations

from typing import Any

from .execution import (
    AgentExecutor,
    AgentRequest,
)


class AgentManager:
    """Central registry and execution interface for KAIRO agents."""

    def __init__(self) -> None:
        self._agents: dict[str, Any] = {}

        self.executor = AgentExecutor()

    def register(
        self,
        agent: Any,
    ) -> None:

        name = getattr(
            agent,
            "name",
            None,
        )

        if not name:
            raise ValueError(
                "Agent must expose a name"
            )

        self._agents[name] = agent

    def unregister(
        self,
        name: str,
    ) -> bool:

        return (
            self._agents.pop(
                name,
                None,
            )
            is not None
        )

    def get(
        self,
        name: str,
    ) -> Any | None:

        return self._agents.get(name)

    def list_agents(self) -> list[str]:
        return sorted(
            self._agents
        )

    def execute(
        self,
        name: str,
        task: str,
    ) -> Any:

        agent = self.get(name)

        if agent is None:
            raise KeyError(
                f"Agent not registered: {name}"
            )

        request = AgentRequest(
            agent=name,
            task=task,
        )

        return self.executor.execute(
            agent,
            request,
        )

    def health(self) -> dict:
        agents = self.list_agents()

        return {
            "status": "ONLINE",
            "count": len(agents),
            "agents": agents,
        }
