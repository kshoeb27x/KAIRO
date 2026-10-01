from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
import inspect
from typing import Any, Callable


@dataclass
class ScheduledJob:
    id: int
    name: str
    interval_seconds: float
    enabled: bool = True
    last_run: str | None = None
    run_count: int = 0


class Scheduler:
    """Lightweight scheduler registry.

    This version registers and manually
    triggers jobs. Background scheduling
    can be added later.
    """

    def __init__(
        self,
        security: Any | None = None,
        should_stop: Callable[[], bool] | None = None,
    ) -> None:

        self._jobs: dict[
            int,
            ScheduledJob,
        ] = {}

        self._functions: dict[
            int,
            Callable[..., Any],
        ] = {}
        self.security = security
        self.should_stop = should_stop

        self._next_id = 1

    def schedule(
        self,
        name: str,
        interval_seconds: float,
        function: Callable[..., Any],
        context: Any | None = None,
    ) -> dict[str, Any]:

        if interval_seconds <= 0:
            raise ValueError(
                "interval_seconds must be positive"
            )

        self._authorize(
            context,
            "runtime.schedule",
            "runtime.schedule",
            name,
        )
        job = ScheduledJob(
            id=self._next_id,
            name=name,
            interval_seconds=interval_seconds,
        )

        self._jobs[job.id] = job
        self._functions[job.id] = function

        self._next_id += 1

        return asdict(job)

    def run(
        self,
        job_id: int,
        context: Any | None = None,
    ) -> Any:

        job = self._jobs[job_id]

        if not job.enabled:
            raise RuntimeError(
                "Scheduled job is disabled"
            )

        function = self._functions[job_id]

        if self.should_stop is not None and self.should_stop():
            operation_context = self._authorize(
                context,
                "runtime.execute",
                "runtime.scheduled.execute",
                job.name,
            )
            self.security.audit_execution(
                operation_context,
                "DENY",
                "EMERGENCY_STOP",
            )
            raise PermissionError(
                "Scheduled execution blocked by emergency stop."
            )

        operation_context = self._authorize(
            context,
            "runtime.execute",
            "runtime.scheduled.execute",
            job.name,
        )

        try:
            parameters = inspect.signature(function).parameters
            accepts_context = (
                "context" in parameters
                or any(
                    parameter.kind == inspect.Parameter.VAR_KEYWORD
                    for parameter in parameters.values()
                )
            )
            result = (
                function(context=operation_context)
                if accepts_context
                else function()
            )
        except Exception as error:
            self.security.audit_execution(
                operation_context,
                "FAILED",
                str(error),
            )
            raise

        job.last_run = (
            datetime.now().isoformat()
        )

        job.run_count += 1
        self.security.audit_execution(
            operation_context,
            "COMPLETED",
        )

        return result

    def cancel(
        self,
        job_id: int,
        context: Any | None = None,
    ) -> bool:
        job = self._jobs.get(job_id)
        operation_context = self._authorize(
            context,
            "runtime.schedule",
            "runtime.schedule.cancel",
            str(job_id),
        )

        if job is None:
            self.security.audit_execution(
                operation_context,
                "NOT_FOUND",
            )
            return False

        job.enabled = False
        self.security.audit_execution(
            operation_context,
            "CANCELLED",
        )

        return True

    def list_jobs(
        self,
    ) -> list[dict[str, Any]]:

        return [
            asdict(job)
            for job in self._jobs.values()
        ]

    def health(self) -> dict[str, Any]:

        return {
            "status": "ONLINE",
            "jobs": len(self._jobs),
            "enabled": sum(
                1
                for job in self._jobs.values()
                if job.enabled
            ),
        }

    def _authorize(
        self,
        context: Any | None,
        permission: str,
        operation: str,
        resource: str,
    ) -> Any:
        if self.security is None or context is None:
            if self.security is not None:
                self.security.audit.record(
                    "AUTHORIZATION",
                    None,
                    operation,
                    "DENY",
                    {
                        "permission": permission,
                        "resource": resource,
                        "reason": "MISSING_CONTEXT_OR_SECURITY",
                    },
                )
            raise PermissionError(
                "Scheduled operations require an authorization context."
            )

        operation_context = context.derive(
            permission=permission,
            operation=operation,
            resource=resource,
        )
        decision = self.security.authorize_context(
            operation_context,
            permission,
        )
        if not decision.allowed:
            self.security.audit_execution(
                operation_context,
                decision.decision,
                decision.reason,
            )
            raise PermissionError(
                f"Scheduled operation denied: {decision.reason}"
            )
        return operation_context
