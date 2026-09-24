"""KAIRO V1 data agent."""

from __future__ import annotations

from agent import AgentResult


class DataAgent:
    name = "data"

    def execute(self, task: str) -> AgentResult:
        task = task.strip()

        if not task:
            raise ValueError("Data task is required.")

        return AgentResult(
            agent=self.name,
            task=task,
            status="COMPLETED",
            result={
                "message": f"Data task received: {task}",
                "type": "structured",
            },
        )
