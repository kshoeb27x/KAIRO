from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import uuid4


@dataclass
class AgentRequest:
    agent: str
    task: str
    request_id: str = ""

    def __post_init__(self) -> None:
        if not self.request_id:
            self.request_id = uuid4().hex


@dataclass
class AgentExecutionResult:
    agent: str
    task: str
    status: str
    result: Any
    started_at: str
    completed_at: str
    request_id: str = ""


class AgentExecutor:
    """Single execution boundary for KAIRO agents."""

    def execute(
        self,
        agent: Any,
        request: AgentRequest,
    ) -> AgentExecutionResult:

        started = datetime.now().isoformat()

        try:
            result = agent.execute(request.task)

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
                request_id=request.request_id,
            )

        except Exception as exc:
            return AgentExecutionResult(
                agent=request.agent,
                task=request.task,
                status="FAILED",
                result=str(exc),
                started_at=started,
                completed_at=datetime.now().isoformat(),
                request_id=request.request_id,
            )