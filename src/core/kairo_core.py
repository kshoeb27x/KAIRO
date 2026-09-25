from __future__ import annotations

from datetime import datetime
from typing import Any

from src.core.runtime_controller import KairoRuntime
from src.core.orchestrator_loader import KairoOrchestrator


class KairoCore:
    """Unified central KAIRO control layer."""

    VERSION = "V2"

    def __init__(self, runtime: Any | None = None) -> None:
        self.name = "KAIRO"
        self.version = self.VERSION
        self.started_at = datetime.now()

        self.runtime = runtime or KairoRuntime()
        self.orchestrator = KairoOrchestrator(self.runtime)

        self._agents: dict[str, Any] = {}

    def register_agent(self, agent: Any) -> None:
        name = getattr(agent, "name", None)

        if not name:
            raise ValueError("Agent must expose a name")

        self._agents[name] = agent

    def unregister_agent(self, name: str) -> bool:
        return self._agents.pop(name, None) is not None

    def list_agents(self) -> list[str]:
        return sorted(self._agents)

    def execute_agent(self, name: str, task: str) -> Any:
        agent = self._agents.get(name)

        if agent is None:
            raise KeyError(f"Agent not registered: {name}")

        return agent.execute(task)

    def create_task(self, name: str) -> dict:
        return self.runtime.create_task(name)

    def respond(self, message: str) -> str:
        return self.orchestrator.dispatch(message)

    def events(self, limit: int = 50) -> list[dict]:
        return self.runtime.recent_events(limit)

    def health(self) -> dict:
        return {
            "system": self.name,
            "version": self.version,
            "core": "ONLINE",
            "mode": "DEVELOPMENT",
            "runtime": self.runtime.status(),
            "agents": self.list_agents(),
            "started_at": self.started_at.isoformat(),
        }

    def status(self) -> dict:
        runtime = self.runtime.status()

        return {
            "system": self.name,
            "version": self.version,
            "core": "ONLINE",
            "mode": "DEVELOPMENT",
            "security": runtime.get("security"),
            "runtime": runtime.get("runtime"),
            "data": runtime.get("data"),
            "network": runtime.get("network"),
            "active_tasks": runtime.get("active_tasks"),
            "completed_tasks": runtime.get("completed_tasks"),
            "failed_tasks": runtime.get("failed_tasks"),
            "active_agents": runtime.get("active_agents"),
            "events": runtime.get("events", 0),
            "tasks": runtime.get("tasks", 0),
            "registered_agents": len(self._agents),
        }
