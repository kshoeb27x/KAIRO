from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class MemoryRecord:
    memory_id: int
    scope: str
    content: str
    metadata: dict[str, Any]
    created_at: str


class MemoryStore:
    """Small durable memory store with scoped text retrieval."""

    def __init__(self, path: str | Path = ":memory:") -> None:
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(self.path)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS memories (
                memory_id INTEGER PRIMARY KEY AUTOINCREMENT,
                scope TEXT NOT NULL,
                content TEXT NOT NULL,
                metadata TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        self._connection.commit()

    def remember(
        self,
        content: str,
        scope: str = "default",
        metadata: dict[str, Any] | None = None,
    ) -> MemoryRecord:
        if not content.strip():
            raise ValueError("Memory content is required.")
        if not scope.strip():
            raise ValueError("Memory scope is required.")

        import json

        created_at = datetime.now().isoformat()
        cursor = self._connection.execute(
            """
            INSERT INTO memories (scope, content, metadata, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (scope, content, json.dumps(metadata or {}, sort_keys=True), created_at),
        )
        self._connection.commit()
        return MemoryRecord(
            memory_id=int(cursor.lastrowid),
            scope=scope,
            content=content,
            metadata=metadata or {},
            created_at=created_at,
        )

    def recall(self, query: str, scope: str | None = None, limit: int = 10) -> list[MemoryRecord]:
        if not query.strip():
            return []
        if limit < 1:
            raise ValueError("Memory recall limit must be positive.")

        import json

        pattern = f"%{query.lower()}%"
        if scope is None:
            rows = self._connection.execute(
                """
                SELECT * FROM memories
                WHERE lower(content) LIKE ?
                ORDER BY memory_id DESC LIMIT ?
                """,
                (pattern, limit),
            ).fetchall()
        else:
            rows = self._connection.execute(
                """
                SELECT * FROM memories
                WHERE scope = ? AND lower(content) LIKE ?
                ORDER BY memory_id DESC LIMIT ?
                """,
                (scope, pattern, limit),
            ).fetchall()

        return [
            MemoryRecord(
                memory_id=int(row["memory_id"]),
                scope=row["scope"],
                content=row["content"],
                metadata=json.loads(row["metadata"]),
                created_at=row["created_at"],
            )
            for row in rows
        ]

    def health(self) -> dict[str, Any]:
        count = self._connection.execute(
            "SELECT COUNT(*) FROM memories"
        ).fetchone()[0]
        return {"status": "ONLINE", "memories": int(count), "durable": self.path != ":memory:"}

    def close(self) -> None:
        self._connection.close()
