from __future__ import annotations

from datetime import datetime

from src.core.runtime_controller import KairoRuntime


class KairoCore:
    """Central KAIRO V1 core."""

    def __init__(self) -> None:
        self.name = "KAIRO"
        self.version = "V1"
        self.started_at = datetime.now()

        self.runtime = KairoRuntime()

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

        message = message.strip()

        if not message:
            return "Please give me a command or question."

        lowered = message.lower()

        if lowered in {"hello", "hi", "hey"}:
            return "Hello. KAIRO V1 is online. Runtime systems are active."

        if lowered == "status":

            status = self.status()

            return (
                f"KAIRO {status['version']} | "
                f"Core: {status['core']} | "
                f"Runtime: {status['runtime']} | "
                f"Security: {status['security']} | "
                f"Tasks: {status['tasks']} | "
                f"Events: {status['events']}"
            )

        if lowered.startswith("create task "):

            name = message[len("create task "):].strip()

            if not name:
                return "Task name is required."

            task = self.create_task(name)

            return (
                f"Task created: {task['name']} "
                f"[{task['id']}]"
            )

        if lowered in {"exit", "quit"}:
            return "__EXIT__"

        return f"I received: {message}"