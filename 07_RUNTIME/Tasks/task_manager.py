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
    completed_at: str | None = None
    result: Any = None
    error: str | None = None


class TaskManager:
    """Creates and tracks runtime tasks."""

    def __init__(
        self,
        state: RuntimeState,
        events: EventBus,
    ) -> None:

        self.state = state
        self.events = events

        self._tasks: dict[
            int,
            Task,
        ] = {}

        self._next_id = 1

    def create(
        self,
        name: str,
    ) -> dict[str, Any]:

        task = Task(
            id=self._next_id,
            name=name,
            status="PENDING",
            created_at=datetime.now().isoformat(),
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

        return asdict(task)

    def get(
        self,
        task_id: int,
    ) -> dict[str, Any] | None:

        task = self._tasks.get(task_id)

        if task is None:
            return None

        return asdict(task)

    def list_tasks(
        self,
    ) -> list[dict[str, Any]]:

        return [
            asdict(task)
            for task in self._tasks.values()
        ]

    def complete(
        self,
        task_id: int,
        result: Any = None,
    ) -> dict[str, Any]:

        task = self._tasks[task_id]

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

        return asdict(task)

    def fail(
        self,
        task_id: int,
        error: str,
    ) -> dict[str, Any]:

        task = self._tasks[task_id]

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

        return asdict(task)
