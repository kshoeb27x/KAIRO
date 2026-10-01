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

        self.orchestrator = KairoOrchestrator(
            runtime=self.runtime
        )

        self.agent_manager = self.orchestrator.agents

    def register_agent(
        self,
        agent: Any,
        authority: Any | None = None,
    ) -> None:
        self.agent_manager.register(
            agent,
            authority,
        )

    def unregister_agent(
        self,
        name: str,
    ) -> bool:
        if self.agent_manager.get(name) is None:
            return False

        control = self.agent_manager.control(name)

        if control.state.value != "STOPPED":
            self.agent_manager.stop(name)

        del self.agent_manager._agents[name]
        del self.agent_manager._controls[name]

        return True

    def list_agents(self) -> list[str]:
        return self.agent_manager.list_agents()

    def execute_agent(
        self,
        name: str,
        task: str,
    ) -> dict[str, Any]:
        execution = self.agent_manager.execute(
            name,
            task,
        )

        return {
            "agent": execution.agent,
            "task": execution.task,
            "status": execution.status,
            "result": execution.result,
            "request_id": execution.request_id,
            "started_at": execution.started_at,
            "completed_at": execution.completed_at,
        }

    def create_task(
        self,
        name: str,
    ) -> dict[str, Any]:
        return self.runtime.create_task(name)

    def respond(
        self,
        message: str,
    ) -> str:
        return self.orchestrator.dispatch(message)

    def events(
        self,
        limit: int = 50,
    ) -> list[dict]:
        return self.runtime.recent_events(limit)

    def health(self) -> dict[str, Any]:
        return {
            "system": self.name,
            "version": self.version,
            "core": "ONLINE",
            "mode": "DEVELOPMENT",
            "runtime": self.runtime.status(),
            "agents": self.list_agents(),
            "agent_health": self.agent_manager.health(),
            "started_at": self.started_at.isoformat(),
        }

    def status(self) -> dict[str, Any]:
        runtime_status = self.runtime.status()

        return {
            "system": self.name,
            "version": self.version,
            "core": "ONLINE",
            "mode": "DEVELOPMENT",
            "runtime": runtime_status,
            "registered_agents": len(
                self.agent_manager.list_agents()
            ),
            "agent_health": self.agent_manager.health(),
            "events": runtime_status.get("events", 0),
            "tasks": runtime_status.get("tasks", 0),
        }
