"""KAIRO V1 research agent."""

from __future__ import annotations

from  agent import AgentResult


class ResearchAgent:
    name = "research"

    def execute(self, task: str) -> AgentResult:
        task = task.strip()

        if not task:
            raise ValueError("Research task is required.")

        return AgentResult(
            agent=self.name,
            task=task,
            status="COMPLETED",
            result=f"Research task received: {task}",
        )
