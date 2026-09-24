from __future__ import annotations

from datetime import datetime

from src.core.runtime_controller import KairoRuntime
from src.core.orchestrator_loader import KairoOrchestrator


class KairoCore:
    """Central KAIRO V1 core."""

    def __init__(self) -> None:
        self.name = "KAIRO"
        self.version = "V1"
        self.started_at = datetime.now()

        self.runtime = KairoRuntime()
        self.orchestrator = KairoOrchestrator(self.runtime)

    def status(self) -> dict:
        runtime_status = self.runtime.status()

        return {
            "system": self.name,
            "version": self.version,
            "core": "ONLINE",
            "mode": "DEVELOPMENT",
            "security": runtime_status["security"],
            "runtime": runtime_status["runtime"],
            "data": runtime_status["data"],
            "network": runtime_status["network"],
            "active_tasks": runtime_status["active_tasks"],
            "completed_tasks": runtime_status["completed_tasks"],
            "failed_tasks": runtime_status["failed_tasks"],
            "active_agents": runtime_status["active_agents"],
            "events": runtime_status["events"],
            "tasks": runtime_status["tasks"],
        }

    def create_task(self, name: str) -> dict:
        return self.runtime.create_task(name)

    def events(self, limit: int = 50) -> list[dict]:
        return self.runtime.recent_events(limit)

    def respond(self, message: str) -> str:
        return self.orchestrator.dispatch(message)
