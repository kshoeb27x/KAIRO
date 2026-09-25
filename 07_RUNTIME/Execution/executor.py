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
    attempts: int = 0
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
        max_attempts: int = 1,
        **kwargs: Any,
    ) -> ExecutionResult:
        if max_attempts < 1:
            raise ValueError("max_attempts must be positive.")

        started = datetime.now().isoformat()

        self.state.running_jobs += 1
        last_error: Exception | None = None

        try:
            self.events.emit("EXECUTION_STARTED", {"name": name})

            for attempt in range(1, max_attempts + 1):
                self.events.emit(
                    "EXECUTION_ATTEMPT",
                    {"name": name, "attempt": attempt},
                )
                try:
                    result = function(*args, **kwargs)
                except Exception as exc:
                    last_error = exc
                    if attempt == max_attempts:
                        break
                    self.events.emit(
                        "EXECUTION_RETRY",
                        {
                            "name": name,
                            "attempt": attempt,
                            "error": str(exc),
                        },
                    )
                    continue

                self.state.completed_jobs += 1
                completed = datetime.now().isoformat()
                self.events.emit(
                    "EXECUTION_COMPLETED",
                    {"name": name, "attempts": attempt},
                )
                return ExecutionResult(
                    status="COMPLETED",
                    result=result,
                    attempts=attempt,
                    started_at=started,
                    completed_at=completed,
                )

            self.state.failed_jobs += 1
            completed = datetime.now().isoformat()
            error = str(last_error) if last_error is not None else "Execution failed."
            self.events.emit(
                "EXECUTION_FAILED",
                {"name": name, "error": error, "attempts": max_attempts},
            )
            return ExecutionResult(
                status="FAILED",
                error=error,
                attempts=max_attempts,
                started_at=started,
                completed_at=completed,
            )
        finally:
            self.state.running_jobs = max(0, self.state.running_jobs - 1)
