from __future__ import annotations

from datetime import datetime, timezone
from threading import Lock
from typing import Any


class EventBus:
    """Simple in-process event system for KAIRO."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._events: list[dict[str, Any]] = []

    def emit(
        self,
        event_type: str,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:

        event = {
            "type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data or {},
        }

        with self._lock:
            self._events.append(event)

        return event

    def recent(self, limit: int = 50) -> list[dict[str, Any]]:
        """Return the most recent events."""

        with self._lock:
            return list(self._events[-limit:])