from __future__ import annotations

from typing import Any


class RAGRetriever:
    """Retrieval layer combining knowledge and vector search."""

    def __init__(
        self,
        knowledge_store: Any,
        vector_store: Any,
    ) -> None:

        self.knowledge = knowledge_store
        self.vector = vector_store

    def retrieve_text(
        self,
        query: str,
        limit: int = 5,
    ) -> list[dict[str, Any]]:

        results = self.knowledge.search(
            query
        )

        return [
            {
                "item_id": item.item_id,
                "title": item.title,
                "content": item.content,
                "metadata": item.metadata,
            }
            for item in results[:limit]
        ]

    def retrieve_vector(
        self,
        query_vector: list[float],
        limit: int = 5,
    ) -> list[dict[str, Any]]:

        return self.vector.search(
            query_vector,
            limit=limit,
        )

    def health(self) -> dict:
        return {
            "status": "ONLINE",
            "knowledge": self.knowledge.health(),
            "vector": self.vector.health(),
        }
