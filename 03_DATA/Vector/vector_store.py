from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any


@dataclass
class VectorRecord:
    vector_id: str
    vector: list[float]
    metadata: dict[str, Any]


class VectorStore:
    """Minimal vector storage and cosine similarity search."""

    def __init__(self) -> None:
        self._records: dict[
            str,
            VectorRecord,
        ] = {}

    def add(
        self,
        vector_id: str,
        vector: list[float],
        metadata: dict[str, Any] | None = None,
    ) -> VectorRecord:

        if not vector_id:
            raise ValueError(
                "vector_id is required"
            )

        if not vector:
            raise ValueError(
                "vector cannot be empty"
            )

        record = VectorRecord(
            vector_id=vector_id,
            vector=[float(x) for x in vector],
            metadata=metadata or {},
        )

        self._records[vector_id] = record

        return record

    @staticmethod
    def cosine_similarity(
        left: list[float],
        right: list[float],
    ) -> float:

        if len(left) != len(right):
            raise ValueError(
                "Vectors must have equal dimensions"
            )

        left_norm = math.sqrt(
            sum(x * x for x in left)
        )

        right_norm = math.sqrt(
            sum(x * x for x in right)
        )

        if left_norm == 0 or right_norm == 0:
            return 0.0

        dot = sum(
            a * b
            for a, b in zip(left, right)
        )

        return dot / (
            left_norm * right_norm
        )

    def search(
        self,
        query: list[float],
        limit: int = 5,
    ) -> list[dict[str, Any]]:

        scored = []

        for record in self._records.values():

            score = self.cosine_similarity(
                query,
                record.vector,
            )

            scored.append(
                {
                    "vector_id": record.vector_id,
                    "score": score,
                    "metadata": record.metadata,
                }
            )

        scored.sort(
            key=lambda item: item["score"],
            reverse=True,
        )

        return scored[:limit]

    def count(self) -> int:
        return len(
            self._records
        )

    def health(self) -> dict:
        return {
            "status": "ONLINE",
            "vectors": len(
                self._records
            ),
        }
