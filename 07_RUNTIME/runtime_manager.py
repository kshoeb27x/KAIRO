from __future__ import annotations

from typing import Any, Callable

from .Events.event_bus import EventBus
from .Execution.executor import RuntimeExecutor
from .Scheduler.scheduler import Scheduler
from .State.runtime_state import RuntimeState
from .Tasks.task_manager import TaskManager
from .Workflows.workflow import Workflow


class RuntimeManager:
    """Unified Runtime V2 control interface."""

    def __init__(self, security: Any | None = None) -> None:

        self.security = security
        self._stopped = False
        self.state = RuntimeState()

        self.events = EventBus()

        self.tasks = TaskManager(
            self.state,
            self.events,
            self.security,
        )

        self.executor = RuntimeExecutor(
            self.state,
            self.events,
            self.security,
            lambda: self._stopped,
        )

        self.scheduler = Scheduler(
            self.security,
            lambda: self._stopped,
        )

        self.events.emit(
            "RUNTIME_STARTED"
        )

    def create_task(
        self,
        name: str,
        context: Any | None = None,
    ) -> dict:
        return self.tasks.create(name, context)

    def complete_task(
        self,
        task_id: int,
        result: Any = None,
        context: Any | None = None,
    ) -> dict:
        completed = self.tasks.complete(
            task_id,
            result,
            context,
        )
        return completed

    def fail_task(
        self,
        task_id: int,
        error: str,
        context: Any | None = None,
    ) -> dict:
        failed = self.tasks.fail(
            task_id,
            error,
            context,
        )
        return failed

    def execute(
        self,
        name: str,
        function: Callable[..., Any],
        *args: Any,
        max_attempts: int = 1,
        context: Any | None = None,
        **kwargs: Any,
    ):
        if self._stopped:
            self._deny(context, "runtime.execute", "runtime.execute", name, "EMERGENCY_STOP")
            raise PermissionError("Runtime is in EMERGENCY STOP.")
        result = self.executor.execute(
            name,
            function,
            *args,
            max_attempts=max_attempts,
            should_stop=lambda: self._stopped,
            context=context,
            **kwargs,
        )
        return result

    def workflow(
        self,
        name: str,
        context: Any | None = None,
    ) -> Workflow:
        if not self._authorize(
            context,
            "runtime.workflow.execute",
            "workflow.create",
            name,
        ):
            raise PermissionError("Workflow creation is not authorized.")
        return Workflow(
            name,
            self.state,
            self.events,
            self.security,
            context,
            lambda: self._stopped,
        )

    def schedule(
        self,
        name: str,
        interval_seconds: float,
        function: Callable[..., Any],
        context: Any | None = None,
    ) -> dict:
        if context is None:
            self._deny(
                None,
                "runtime.schedule",
                "runtime.schedule",
                name,
                "MISSING_CONTEXT",
            )
            raise PermissionError("Scheduling is not authorized.")

        def execute_scheduled(context: Any) -> Any:
            return self.execute(
                f"scheduled:{name}",
                function,
                context=context,
            )

        scheduled = self.scheduler.schedule(
            name,
            interval_seconds,
            execute_scheduled,
            context=context.derive(
                permission="runtime.schedule",
                operation="runtime.schedule",
                resource=name,
            ),
        )
        self.security.audit_execution(context, "SCHEDULED")
        return scheduled

    def cancel_schedule(
        self,
        job_id: int,
        context: Any | None = None,
    ) -> bool:
        if context is None:
            self._deny(
                None,
                "runtime.schedule",
                "runtime.schedule.cancel",
                str(job_id),
                "MISSING_CONTEXT",
            )
            raise PermissionError(
                "Schedule cancellation is not authorized."
            )
        return self.scheduler.cancel(
            job_id,
            context.derive(
                permission="runtime.schedule",
                operation="runtime.schedule.cancel",
                resource=str(job_id),
            ),
        )

    def emergency_stop(self, context: Any | None = None) -> None:
        if not self._authorize(
            context,
            "runtime.emergency_stop",
            "runtime.emergency_stop",
            "runtime",
        ):
            raise PermissionError("Emergency stop is not authorized.")
        self._stopped = True
        self.state.status = "EMERGENCY_STOP"
        self.security.audit_execution(context, "STOPPED")

    def emergency_reset(self, context: Any | None = None) -> None:
        if not self._authorize(
            context,
            "security.approve",
            "runtime.emergency_reset",
            "runtime",
            authority_required=30,
        ):
            raise PermissionError("Emergency reset is not authorized.")
        self._stopped = False
        self.state.status = "ONLINE"
        self.security.audit_execution(context, "RESET")

    def _authorize(
        self,
        context: Any | None,
        permission: str,
        operation: str,
        resource: str,
        authority_required: int = 10,
    ) -> bool:
        if context is None or self.security is None:
            self._deny(context, permission, operation, resource, "MISSING_CONTEXT_OR_SECURITY")
            return False
        operation_context = context.derive(
            permission=permission,
            operation=operation,
            resource=resource,
        )
        from importlib import import_module

        authority_level = import_module(
            "06_SECURITY.Authority.authority"
        ).AuthorityLevel(authority_required)
        decision = self.security.authorize_context(
            operation_context,
            permission,
            authority_level,
        )
        if not decision.allowed:
            self.security.audit_execution(
                operation_context,
                decision.decision,
                decision.reason,
            )
            return False
        return True

    def _deny(
        self,
        context: Any | None,
        permission: str,
        operation: str,
        resource: str,
        reason: str,
    ) -> None:
        if self.security is None:
            return
        if context is None:
            self.security.audit.record(
                "AUTHORIZATION",
                None,
                operation,
                "DENY",
                {"permission": permission, "resource": resource, "reason": reason},
            )
            return
        denied = context.derive(
            permission=permission,
            operation=operation,
            resource=resource,
        )
        self.security.audit_execution(denied, "DENY", reason)

    def status(self) -> dict:

        snapshot = self.state.snapshot()

        snapshot["events"] = (
            self.events.count()
        )

        snapshot["tasks"] = self.tasks.count()

        snapshot["scheduled_jobs"] = len(
            self.scheduler.list_jobs()
        )

        return snapshot

    def recent_events(self, limit: int = 50) -> list[dict]:
        return self.events.recent(limit)

    def health(self) -> dict:

        return {
            "status": self.state.status,
            "runtime": self.status(),
            "scheduler": self.scheduler.health(),
        }
