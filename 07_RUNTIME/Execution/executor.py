from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import inspect
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
        security: Any | None = None,
        should_stop: Callable[[], bool] | None = None,
    ) -> None:

        self.state = state
        self.events = events
        self.security = security
        self.should_stop = should_stop

    def execute(
        self,
        name: str,
        function: Callable[..., Any],
        *args: Any,
        max_attempts: int = 1,
        should_stop: Callable[[], bool] | None = None,
        context: Any | None = None,
        **kwargs: Any,
    ) -> ExecutionResult:
        if max_attempts < 1:
            raise ValueError("max_attempts must be positive.")
        if self.security is None or context is None:
            if self.security is not None:
                self.security.audit.record(
                    "AUTHORIZATION",
                    None,
                    "runtime.execute",
                    "DENY",
                    {
                        "permission": "runtime.execute",
                        "resource": name,
                        "reason": "MISSING_CONTEXT_OR_SECURITY",
                    },
                )
            raise PermissionError(
                "Runtime execution requires an authorization context."
            )

        execution_context = context.derive(
            permission="runtime.execute",
            operation="runtime.execute",
            resource=name,
        )
        decision = self.security.authorize_context(
            execution_context,
            "runtime.execute",
        )
        if not decision.allowed:
            self.security.audit_execution(
                execution_context,
                decision.decision,
                decision.reason,
            )
            raise PermissionError(
                f"Runtime execution denied: {decision.reason}"
            )

        call_kwargs = dict(kwargs)
        try:
            signature = inspect.signature(function)
        except (TypeError, ValueError):
            signature = None
        if signature is not None:
            parameters = signature.parameters
            accepts_context = (
                "context" in parameters
                or any(
                    parameter.kind == inspect.Parameter.VAR_KEYWORD
                    for parameter in parameters.values()
                )
            )
            try:
                bound = signature.bind_partial(*args, **call_kwargs)
            except TypeError:
                bound = None
            if (
                accepts_context
                and bound is not None
                and "context" not in bound.arguments
            ):
                call_kwargs["context"] = execution_context

        started = datetime.now().isoformat()

        self.state.running_jobs += 1
        last_error: Exception | None = None

        try:
            event_context = {
                "identity": (
                    context.caller_identity
                    if context is not None
                    else None
                ),
                "agent_identity": (
                    context.agent_identity
                    if context is not None
                    else None
                ),
                "correlation_id": (
                    context.correlation_id
                    if context is not None
                    else None
                ),
            }
            self.events.emit(
                "EXECUTION_STARTED",
                {"name": name, **event_context},
            )

            for attempt in range(1, max_attempts + 1):
                if (
                    (should_stop is not None and should_stop())
                    or (
                        self.should_stop is not None
                        and self.should_stop()
                    )
                ):
                    last_error = RuntimeError("Execution cancelled by emergency stop.")
                    break
                self.events.emit(
                    "EXECUTION_ATTEMPT",
                    {"name": name, "attempt": attempt},
                )
                try:
                    result = function(*args, **call_kwargs)
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
                self.security.audit_execution(
                    execution_context,
                    "COMPLETED",
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
            self.security.audit_execution(
                execution_context,
                "FAILED",
                error,
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
