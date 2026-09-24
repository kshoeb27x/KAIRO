from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_ROOT = PROJECT_ROOT / "07_RUNTIME"

sys.path.insert(0, str(RUNTIME_ROOT))

from Events.event_bus import EventBus
from State.runtime_state import RuntimeState
from Task_Manager.task_manager import TaskManager


class KairoRuntime:
    """Runtime controller connecting KAIRO state, events and tasks."""

    def __init__(self) -> None:
        self.state = RuntimeState()
        self.events = EventBus()
        self.tasks = TaskManager(self.state, self.events)

        self.events.emit("RUNTIME_STARTED")

    def status(self) -> dict:
        """Return complete runtime status."""

        snapshot = self.state.snapshot()

        snapshot["events"] = len(self.events.recent())
        snapshot["tasks"] = len(self.tasks.list_tasks())

        return snapshot

    def create_task(self, name: str) -> dict:
        """Create a new KAIRO task."""

        return self.tasks.create(name)

    def recent_events(self, limit: int = 50) -> list[dict]:
        """Return recent runtime events."""

        return self.events.recent(limit)