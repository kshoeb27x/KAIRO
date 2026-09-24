from __future__ import annotations

from datetime import datetime
from typing import Any


class RuntimeState:
    """Tracks runtime lifecycle and execution counters."""

    def __init__(self) -> None:
        self.started_at = datetime.now().isoformat()
        self.status = "ONLINE"

        self.active_tasks = 0
        self.completed_tasks = 0
        self.failed_tasks = 0

        self.active_workflows = 0
        self.completed_workflows = 0
        self.failed_workflows = 0

        self.running_jobs = 0
        self.completed_jobs = 0
        self.failed_jobs = 0

    def snapshot(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "started_at": self.started_at,
            "active_tasks": self.active_tasks,
            "completed_tasks": self.completed_tasks,
            "failed_tasks": self.failed_tasks,
            "active_workflows": self.active_workflows,
            "completed_workflows": self.completed_workflows,
            "failed_workflows": self.failed_workflows,
            "running_jobs": self.running_jobs,
            "completed_jobs": self.completed_jobs,
            "failed_jobs": self.failed_jobs,
        }
