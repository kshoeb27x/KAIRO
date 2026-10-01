from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from ..Database.database import Database


@dataclass
class VectorRecord:
    vector_id: str
    vector: list[float]
    metadata: dict[str, Any]


class VectorStore:
    """SQLite-backed vector records with cosine similarity search."""

    COLLECTION = "vectors"

    def __init__(self, database: Database | None = None) -> None:
        self.database = database or Database()

    def add(
        self,
        vector_id: str,
        vector: list[float],
        metadata: dict[str, Any] | None = None,
    ) -> VectorRecord:
        if not vector_id:
            raise ValueError("vector_id is required")
        if not vector:
            raise ValueError("vector cannot be empty")

        record = VectorRecord(
            vector_id=vector_id,
            vector=[float(value) for value in vector],
            metadata=metadata or {},
        )
        self.database.insert(
            self.COLLECTION,
            vector_id,
            {
                "vector_id": record.vector_id,
                "vector": record.vector,
                "metadata": record.metadata,
            },
        )
        return record

    @staticmethod
    def cosine_similarity(
        left: list[float],
        right: list[float],
    ) -> float:
        if len(left) != len(right):
            raise ValueError("Vectors must have equal dimensions")

        left_norm = math.sqrt(sum(value * value for value in left))
        right_norm = math.sqrt(sum(value * value for value in right))
        if left_norm == 0 or right_norm == 0:
            return 0.0

        dot = sum(a * b for a, b in zip(left, right))
        return dot / (left_norm * right_norm)

    def search(
        self,
        query: list[float],
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        if limit < 1:
            raise ValueError("limit must be positive")
        if not query:
            raise ValueError("query vector cannot be empty")

        scored = []
        for item in self.database.list_collection(self.COLLECTION):
            score = self.cosine_similarity(
                [float(value) for value in query],
                item["vector"],
            )
            scored.append({
                "vector_id": item["vector_id"],
                "score": score,
                "metadata": item["metadata"],
            })

        scored.sort(
            key=lambda item: item["score"],
            reverse=True,
        )
        return scored[:limit]

    def count(self) -> int:
        return len(self.database.list_collection(self.COLLECTION))

    def health(self) -> dict[str, Any]:
        return {
            "status": "ONLINE",
            "vectors": self.count(),
            "durable": self.database.health()["durable"],
        }
