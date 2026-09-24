"""KAIRO V1 coding agent."""

from __future__ import annotations

from agent import AgentResult


class CodingAgent:
    name = "coding"

    def execute(self, task: str) -> AgentResult:
        task = task.strip()

        if not task:
            raise ValueError("Coding task is required.")

        return AgentResult(
            agent=self.name,
            task=task,
            status="COMPLETED",
            result=f"Coding task received: {task}",
        )
