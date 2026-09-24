from __future__ import annotations

from datetime import datetime, timezone
from threading import Lock


class RuntimeState:
    """Central runtime state for KAIRO."""

    def __init__(self) -> None:
        self._lock = Lock()

        self.started_at = datetime.now(timezone.utc)

        self.core = "ONLINE"
        self.runtime = "ONLINE"
        self.security = "ACTIVE"
        self.data = "READY"
        self.network = "RESTRICTED"

        self.active_tasks = 0
        self.completed_tasks = 0
        self.failed_tasks = 0

        self.active_agents = 0

    def snapshot(self) -> dict:
        """Return a safe snapshot of the current runtime state."""

        with self._lock:
            return {
                "core": self.core,
                "runtime": self.runtime,
                "security": self.security,
                "data": self.data,
                "network": self.network,
                "active_tasks": self.active_tasks,
                "completed_tasks": self.completed_tasks,
                "failed_tasks": self.failed_tasks,
                "active_agents": self.active_agents,
                "started_at": self.started_at.isoformat(),
            }