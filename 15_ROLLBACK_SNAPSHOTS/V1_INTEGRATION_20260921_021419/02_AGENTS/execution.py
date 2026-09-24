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
    """Executes registered agents through one execution boundary."""

    def execute(
        self,
        agent: Any,
        request: AgentRequest,
    ) -> AgentExecutionResult:

        started = datetime.now().isoformat()

        try:
            result = agent.execute(
                request.task
            )

            if hasattr(result, "status"):
                status = result.status

            elif isinstance(result, dict):
                status = result.get(
                    "status",
                    "COMPLETED",
                )

            else:
                status = "COMPLETED"

            return AgentExecutionResult(
                agent=request.agent,
                task=request.task,
                status=status,
                result=result,
                started_at=started,
                completed_at=datetime.now().isoformat(),
            )

        except Exception as exc:
            return AgentExecutionResult(
                agent=request.agent,
                task=request.task,
                status="FAILED",
                result=str(exc),
                started_at=started,
                completed_at=datetime.now().isoformat(),
            )
