from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable

from ..Events.event_bus import EventBus
from ..State.runtime_state import RuntimeState


@dataclass
class ExecutionResult:
    status: str
    result: Any = None
    error: str | None = None
    started_at: str = ""
    completed_at: str = ""


class RuntimeExecutor:
    """Controlled execution boundary for runtime jobs."""

    def __init__(
        self,
        state: RuntimeState,
        events: EventBus,
    ) -> None:
        self.state = state
        self.events = events

    def execute(
        self,
        name: str,
        function: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> ExecutionResult:

        started = datetime.now().isoformat()

        self.state.running_jobs += 1

        self.events.emit(
            "EXECUTION_STARTED",
            {
                "name": name,
            },
        )

        try:
            result = function(
                *args,
                **kwargs,
            )

            self.state.running_jobs = max(
                0,
                self.state.running_jobs - 1,
            )

            self.state.completed_jobs += 1

            completed = datetime.now().isoformat()

            self.events.emit(
                "EXECUTION_COMPLETED",
                {
                    "name": name,
                },
            )

            return ExecutionResult(
                status="COMPLETED",
                result=result,
                started_at=started,
                completed_at=completed,
            )

        except Exception as exc:
            self.state.running_jobs = max(
                0,
                self.state.running_jobs - 1,
            )

            self.state.failed_jobs += 1

            completed = datetime.now().isoformat()

            self.events.emit(
                "EXECUTION_FAILED",
                {
                    "name": name,
                    "error": str(exc),
                },
            )

            return ExecutionResult(
                status="FAILED",
                error=str(exc),
                started_at=started,
                completed_at=completed,
            )
