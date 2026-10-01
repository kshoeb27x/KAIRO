from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from ..Database.database import Database


@dataclass
class KnowledgeItem:
    item_id: str
    title: str
    content: str
    metadata: dict[str, Any]
    created_at: str


class KnowledgeStore:
    """Stores structured knowledge records in the shared collection database."""

    COLLECTION = "knowledge"

    def __init__(self, database: Database | None = None) -> None:
        self.database = database or Database()

    def add(
        self,
        item_id: str,
        title: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> KnowledgeItem:
        if not item_id:
            raise ValueError("item_id is required")

        value = {
            "item_id": item_id,
            "title": title,
            "content": content,
            "metadata": metadata or {},
            "created_at": datetime.now().isoformat(),
        }
        self.database.insert(self.COLLECTION, item_id, value)
        return self._from_value(value)

    def get(self, item_id: str) -> KnowledgeItem | None:
        value = self.database.get(self.COLLECTION, item_id)
        if value is None:
            return None
        return self._from_value(value)

    def search(self, query: str) -> list[KnowledgeItem]:
        query_lower = query.lower()
        return [
            item
            for item in self.list_items()
            if query_lower in f"{item.title} {item.content}".lower()
        ]

    def list_items(self) -> list[KnowledgeItem]:
        return [
            self._from_value(value)
            for value in self.database.list_collection(self.COLLECTION)
        ]

    def health(self) -> dict[str, Any]:
        return {
            "status": "ONLINE",
            "items": len(self.database.list_collection(self.COLLECTION)),
            "durable": self.database.health()["durable"],
        }

    @staticmethod
    def _from_value(value: dict[str, Any]) -> KnowledgeItem:
        return KnowledgeItem(
            item_id=value["item_id"],
            title=value["title"],
            content=value["content"],
            metadata=value["metadata"],
            created_at=value["created_at"],
        )
