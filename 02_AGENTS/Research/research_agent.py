"""KAIRO V1 research agent."""

from __future__ import annotations

from typing import Any

from  agent import AgentResult


class ResearchAgent:
    name = "research"

    def execute(
        self,
        task: str,
        context: Any | None = None,
    ) -> AgentResult:
        task = task.strip()

        if not task:
            raise ValueError("Research task is required.")

        return AgentResult(
            agent=self.name,
            task=task,
            status="UNAVAILABLE",
            result=(
                "Research execution is unavailable: no authorized "
                "research provider is configured."
            ),
        )
