"""KAIRO V1 agent manager."""

from __future__ import annotations

from typing import Any

from execution import AgentExecutor, AgentRequest


class AgentManager:
    """Registers and executes KAIRO agents through one execution layer."""

    def __init__(self) -> None:
        self._agents: dict[str, Any] = {}
        self.executor = AgentExecutor()

    def register(self, agent: Any) -> None:
        name = getattr(agent, "name", "").strip()

        if not name:
            raise ValueError("Agent name is required.")

        self._agents[name] = agent

    def get(self, name: str) -> Any | None:
        return self._agents.get(name.strip())

    def execute(self, name: str, task: str) -> Any:
        agent = self.get(name)

        if agent is None:
            raise ValueError(f"Agent not found: {name}")

        request = AgentRequest(
            agent=name.strip(),
            task=task,
        )

        return self.executor.execute(agent, request)

    def list_agents(self) -> list[str]:
        return sorted(self._agents)
