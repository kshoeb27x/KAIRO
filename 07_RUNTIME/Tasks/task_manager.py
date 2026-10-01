from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

from ..Events.event_bus import EventBus
from ..State.runtime_state import RuntimeState


@dataclass
class Task:
    id: int
    name: str
    status: str
    created_at: str
    identity: str | None = None
    agent_identity: str | None = None
    correlation_id: str | None = None
    completed_at: str | None = None
    result: Any = None
    error: str | None = None


class TaskManager:
    """Creates and tracks runtime tasks."""

    def __init__(
        self,
        state: RuntimeState,
        events: EventBus,
        security: Any | None = None,
    ) -> None:

        self.state = state
        self.events = events
        self.security = security

        self._tasks: dict[
            int,
            Task,
        ] = {}

        self._next_id = 1

    def create(
        self,
        name: str,
        context: Any | None = None,
    ) -> dict[str, Any]:
        operation_context = self._authorize(
            context,
            "runtime.task.create",
            "task.create",
            name,
        )

        task = Task(
            id=self._next_id,
            name=name,
            status="PENDING",
            created_at=datetime.now().isoformat(),
            identity=(
                context.caller_identity
                if context is not None
                else None
            ),
            agent_identity=(
                context.agent_identity
                if context is not None
                else None
            ),
            correlation_id=(
                context.correlation_id
                if context is not None
                else None
            ),
        )

        self._tasks[task.id] = task

        self._next_id += 1

        self.state.active_tasks += 1

        self.events.emit(
            "TASK_CREATED",
            {
                "task_id": task.id,
                "name": name,
            },
        )

        self.security.audit_execution(operation_context, "CREATED")
        return asdict(task)

    def get(
        self,
        task_id: int,
        context: Any | None = None,
    ) -> dict[str, Any] | None:
        operation_context = self._authorize(
            context,
            "runtime.task.read",
            "task.read",
            str(task_id),
        )

        task = self._tasks.get(task_id)

        if task is None:
            self.security.audit_execution(operation_context, "NOT_FOUND")
            return None

        self._ensure_task_visible(task, operation_context)
        self.security.audit_execution(operation_context, "READ")
        return asdict(task)

    def list_tasks(
        self,
        context: Any | None = None,
    ) -> list[dict[str, Any]]:
        operation_context = self._authorize(
            context,
            "runtime.task.read",
            "task.list",
            "tasks",
        )
        identity = self.security.identity.get(
            operation_context.caller_identity
        )
        is_admin = (
            identity is not None
            and self.security.authority.get(
                operation_context.caller_identity
            ).value >= 30
        )
        visible_tasks = (
            self._tasks.values()
            if is_admin
            else (
                task
                for task in self._tasks.values()
                if task.identity == operation_context.caller_identity
            )
        )
        self.security.audit_execution(operation_context, "READ")

        return [
            asdict(task)
            for task in visible_tasks
        ]

    def count(self) -> int:
        return len(self._tasks)

    def complete(
        self,
        task_id: int,
        result: Any = None,
        context: Any | None = None,
    ) -> dict[str, Any]:
        operation_context = self._authorize(
            context,
            "runtime.execute",
            "task.complete",
            str(task_id),
        )

        task = self._tasks[task_id]
        self._ensure_task_visible(task, operation_context)

        if task.status == "COMPLETED":
            return asdict(task)

        task.status = "COMPLETED"
        task.result = result

        task.completed_at = (
            datetime.now().isoformat()
        )

        self.state.active_tasks = max(
            0,
            self.state.active_tasks - 1,
        )

        self.state.completed_tasks += 1

        self.events.emit(
            "TASK_COMPLETED",
            {
                "task_id": task_id,
            },
        )

        self.security.audit_execution(operation_context, "COMPLETED")
        return asdict(task)

    def fail(
        self,
        task_id: int,
        error: str,
        context: Any | None = None,
    ) -> dict[str, Any]:
        operation_context = self._authorize(
            context,
            "runtime.execute",
            "task.fail",
            str(task_id),
        )

        task = self._tasks[task_id]
        self._ensure_task_visible(task, operation_context)

        task.status = "FAILED"
        task.error = error

        task.completed_at = (
            datetime.now().isoformat()
        )

        self.state.active_tasks = max(
            0,
            self.state.active_tasks - 1,
        )

        self.state.failed_tasks += 1

        self.events.emit(
            "TASK_FAILED",
            {
                "task_id": task_id,
                "error": error,
            },
        )

        self.security.audit_execution(
            operation_context,
            "FAILED",
            error,
        )
        return asdict(task)

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
                "Task operation requires an authorization context."
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
                f"Task operation denied: {decision.reason}"
            )
        return operation_context

    def _ensure_task_visible(self, task: Task, context: Any) -> None:
        identity = self.security.identity.get(context.caller_identity)
        is_admin = (
            identity is not None
            and self.security.authority.get(
                context.caller_identity
            ).value >= 30
        )
        if not is_admin and task.identity != context.caller_identity:
            self.security.audit_execution(
                context,
                "DENY",
                "TASK_OWNERSHIP_MISMATCH",
            )
            raise PermissionError("Task is not visible to this identity.")
