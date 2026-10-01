"""KAIRO V1 data agent."""

from __future__ import annotations

from typing import Any

from agent import AgentResult


class DataAgent:
    name = "data"

    def execute(
        self,
        task: str,
        context: Any | None = None,
    ) -> AgentResult:
        task = task.strip()

        if not task:
            raise ValueError("Data task is required.")

        return AgentResult(
            agent=self.name,
            task=task,
            status="UNAVAILABLE",
            result=(
                "Data analysis is unavailable: no authorized "
                "data-analysis backend is configured."
            ),
        )
