from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class KnowledgeItem:
    item_id: str
    title: str
    content: str
    metadata: dict[str, Any]
    created_at: str


class KnowledgeStore:
    """Stores structured knowledge records."""

    def __init__(self) -> None:
        self._items: dict[
            str,
            KnowledgeItem,
        ] = {}

    def add(
        self,
        item_id: str,
        title: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> KnowledgeItem:

        if not item_id:
            raise ValueError(
                "item_id is required"
            )

        item = KnowledgeItem(
            item_id=item_id,
            title=title,
            content=content,
            metadata=metadata or {},
            created_at=datetime.now().isoformat(),
        )

        self._items[item_id] = item

        return item

    def get(
        self,
        item_id: str,
    ) -> KnowledgeItem | None:

        return self._items.get(
            item_id
        )

    def search(
        self,
        query: str,
    ) -> list[KnowledgeItem]:

        query_lower = query.lower()

        results = []

        for item in self._items.values():

            text = (
                item.title
                + " "
                + item.content
            ).lower()

            if query_lower in text:
                results.append(item)

        return results

    def list_items(
        self,
    ) -> list[KnowledgeItem]:

        return list(
            self._items.values()
        )

    def health(self) -> dict:
        return {
            "status": "ONLINE",
            "items": len(
                self._items
            ),
        }
