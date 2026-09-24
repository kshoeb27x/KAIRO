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

    def __init__(self) -> None:
        self.state = RuntimeState()
        self.events = EventBus()

        self.tasks = TaskManager(
            self.state,
            self.events,
        )

        self.executor = RuntimeExecutor(
            self.state,
            self.events,
        )

        self.scheduler = Scheduler()

        self.events.emit(
            "RUNTIME_STARTED"
        )

    def create_task(
        self,
        name: str,
    ) -> dict:
        return self.tasks.create(name)

    def complete_task(
        self,
        task_id: int,
        result: Any = None,
    ) -> dict:
        return self.tasks.complete(
            task_id,
            result,
        )

    def fail_task(
        self,
        task_id: int,
        error: str,
    ) -> dict:
        return self.tasks.fail(
            task_id,
            error,
        )

    def execute(
        self,
        name: str,
        function: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ):
        return self.executor.execute(
            name,
            function,
            *args,
            **kwargs,
        )

    def workflow(
        self,
        name: str,
    ) -> Workflow:
        return Workflow(
            name,
            self.state,
            self.events,
        )

    def schedule(
        self,
        name: str,
        interval_seconds: float,
        function: Callable[..., Any],
    ) -> dict:
        return self.scheduler.schedule(
            name,
            interval_seconds,
            function,
        )

    def status(self) -> dict:
        snapshot = self.state.snapshot()

        snapshot["events"] = self.events.count()
        snapshot["tasks"] = len(
            self.tasks.list_tasks()
        )
        snapshot["scheduled_jobs"] = len(
            self.scheduler.list_jobs()
        )

        return snapshot

    def health(self) -> dict:
        return {
            "status": "ONLINE",
            "runtime": self.status(),
            "scheduler": self.scheduler.health(),
        }
