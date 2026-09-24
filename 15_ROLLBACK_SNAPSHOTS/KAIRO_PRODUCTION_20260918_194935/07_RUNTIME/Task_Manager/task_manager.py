from __future__ import annotations

from datetime import datetime, timezone
from threading import Lock
from uuid import uuid4

from Events.event_bus import EventBus
from State.runtime_state import RuntimeState


class TaskManager:
    """Create and track KAIRO runtime tasks."""

    def __init__(
        self,
        state: RuntimeState,
        events: EventBus,
    ) -> None:

        self.state = state
        self.events = events

        self._lock = Lock()
        self._tasks: dict[str, dict] = {}

    def create(self, name: str) -> dict:

        name = name.strip()

        if not name:
            raise ValueError("Task name cannot be empty.")

        task_id = str(uuid4())

        task = {
            "id": task_id,
            "name": name,
            "status": "PENDING",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        with self._lock:
            self._tasks[task_id] = task

        self.events.emit(
            "TASK_CREATED",
            {
                "task_id": task_id,
                "name": name,
            },
        )

        return task

    def list_tasks(self) -> list[dict]:

        with self._lock:
            return list(self._tasks.values())

    def get(self, task_id: str) -> dict | None:

        with self._lock:
            return self._tasks.get(task_id)