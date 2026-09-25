from __future__ import annotations

from typing import Any


class DataManager:
    """Unified interface over KAIRO data components."""

    def __init__(
        self,
        database: Any,
        knowledge: Any,
        vector: Any,
        memory: Any | None = None,
    ) -> None:

        self.database = database
        self.knowledge = knowledge
        self.vector = vector
        self.memory = memory

    def health(self) -> dict:

        return {
            "status": "ONLINE",
            "database": self.database.health(),
            "knowledge": self.knowledge.health(),
            "vector": self.vector.health(),
            "memory": self.memory.health() if self.memory is not None else {
                "status": "DISABLED",
            },
        }

    def summary(self) -> dict:

        return {
            "collections": self.database.collections(),
            "knowledge_items": len(
                self.knowledge.list_items()
            ),
            "vectors": self.vector.count(),
            "memories": (
                self.memory.health()["memories"]
                if self.memory is not None
                else 0
            ),
        }
