"""KAIRO V1 agent execution framework."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class AgentRequest:
    agent: str
    task: str
    request_id: str = ""


@dataclass
class AgentExecutionResult:
    agent: str
    task: str
    status: str
    result: Any
    started_at: str
    completed_at: str


class AgentExecutor:
    """Standard execution wrapper for all KAIRO agents."""

    def execute(self, agent: Any, request: AgentRequest) -> AgentExecutionResult:
        task = request.task.strip()

        if not task:
            raise ValueError("Agent task is required.")

        started = datetime.now().isoformat()

        try:
            output = agent.execute(task)

            return AgentExecutionResult(
                agent=request.agent,
                task=task,
                status="COMPLETED",
                result=getattr(output, "result", output),
                started_at=started,
                completed_at=datetime.now().isoformat(),
            )

        except Exception as exc:
            return AgentExecutionResult(
                agent=request.agent,
                task=task,
                status="FAILED",
                result=str(exc),
                started_at=started,
                completed_at=datetime.now().isoformat(),
            )
