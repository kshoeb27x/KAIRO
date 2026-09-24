"""Lightweight event bus for the JARVIS voice pipeline."""

from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Callable
from typing import Any


class WakeEventBus:
    """Dispatches wake word events to registered listeners."""

    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger
        self._listeners: dict[str, list[Callable[..., None]]] = defaultdict(list)

    def subscribe(self, event_type: str, callback: Callable[..., None]) -> None:
        """Register a callback for a specific event type."""
        self._listeners[event_type].append(callback)
        self._logger.debug("Subscribed to event: %s", event_type)

    def emit(self, event_type: str, **kwargs: Any) -> None:
        """Emit an event to all registered listeners."""
        self._logger.debug("Emitting event: %s", event_type)
        for callback in self._listeners.get(event_type, []):
            try:
                callback(**kwargs)
            except Exception:
                self._logger.exception("Error in event listener for %s", event_type)
