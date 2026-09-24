"""KAIRO V1 memory layer."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class Memory:
    key: str
    value: str
    created_at: str


class KairoMemory:
    """Simple in-process memory store for KAIRO V1."""

    def __init__(self) -> None:
        self._store: dict[str, Memory] = {}

    def remember(self, key: str, value: str) -> Memory:
        key = key.strip()
        value = value.strip()

        if not key:
            raise ValueError("Memory key is required.")

        if not value:
            raise ValueError("Memory value is required.")

        item = Memory(
            key=key,
            value=value,
            created_at=datetime.now().isoformat(),
        )

        self._store[key] = item
        return item

    def recall(self, key: str) -> Memory | None:
        return self._store.get(key.strip())

    def forget(self, key: str) -> bool:
        return self._store.pop(key.strip(), None) is not None

    def snapshot(self) -> dict:
        return {
            key: {
                "value": item.value,
                "created_at": item.created_at,
            }
            for key, item in self._store.items()
        }
