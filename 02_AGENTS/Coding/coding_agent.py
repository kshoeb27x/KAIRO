"""KAIRO V1 coding agent."""

from __future__ import annotations

from typing import Any

from agent import AgentResult


class CodingAgent:
    name = "coding"

    def execute(
        self,
        task: str,
        context: Any | None = None,
    ) -> AgentResult:
        task = task.strip()

        if not task:
            raise ValueError("Coding task is required.")

        return AgentResult(
            agent=self.name,
            task=task,
            status="UNAVAILABLE",
            result=(
                "Coding execution is unavailable: no authorized "
                "engineering backend is configured."
            ),
        )
