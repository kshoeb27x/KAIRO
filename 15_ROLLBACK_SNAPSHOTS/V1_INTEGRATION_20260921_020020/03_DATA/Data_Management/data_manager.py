from __future__ import annotations

from typing import Any


class DataManager:
    """Unified interface over KAIRO data components."""

    def __init__(
        self,
        database: Any,
        knowledge: Any,
        vector: Any,
    ) -> None:

        self.database = database
        self.knowledge = knowledge
        self.vector = vector

    def health(self) -> dict:

        return {
            "status": "ONLINE",
            "database": self.database.health(),
            "knowledge": self.knowledge.health(),
            "vector": self.vector.health(),
        }

    def summary(self) -> dict:

        return {
            "collections": self.database.collections(),
            "knowledge_items": len(
                self.knowledge.list_items()
            ),
            "vectors": self.vector.count(),
        }
