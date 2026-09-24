from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Callable


@dataclass
class Event:
    name: str
    payload: dict[str, Any]
    created_at: str


class EventBus:
    """In-process event bus for KAIRO runtime coordination."""

    def __init__(self) -> None:
        self._events: list[Event] = []

        self._subscribers: dict[
            str,
            list[Callable[[Event], None]],
        ] = {}

    def subscribe(
        self,
        event_name: str,
        callback: Callable[[Event], None],
    ) -> None:
        self._subscribers.setdefault(
            event_name,
            [],
        ).append(callback)

    def emit(
        self,
        name: str,
        payload: dict[str, Any] | None = None,
    ) -> Event:

        event = Event(
            name=name,
            payload=payload or {},
            created_at=datetime.now().isoformat(),
        )

        self._events.append(event)

        for callback in self._subscribers.get(
            name,
            [],
        ):
            callback(event)

        return event

    def recent(
        self,
        limit: int = 50,
    ) -> list[dict[str, Any]]:

        events = self._events[-limit:]

        return [
            asdict(event)
            for event in events
        ]

    def count(self) -> int:
        return len(self._events)
