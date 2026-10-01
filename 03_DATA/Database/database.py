from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sqlite3
from typing import Any


class Database:
    """SQLite-backed collection store with an in-memory default."""

    def __init__(self, path: str | Path = ":memory:") -> None:
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(self.path)
        self._connection.row_factory = sqlite3.Row
        self._connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS collections (
                name TEXT PRIMARY KEY
            );
            CREATE TABLE IF NOT EXISTS records (
                collection TEXT NOT NULL,
                record_key TEXT NOT NULL,
                value TEXT NOT NULL,
                PRIMARY KEY (collection, record_key),
                FOREIGN KEY (collection) REFERENCES collections(name)
            );
            """
        )
        self._connection.commit()

    def create_collection(self, name: str) -> None:
        if not name:
            raise ValueError("Collection name is required")
        self._connection.execute(
            "INSERT OR IGNORE INTO collections (name) VALUES (?)",
            (name,),
        )
        self._connection.commit()

    def insert(
        self,
        collection: str,
        key: str,
        value: dict[str, Any],
    ) -> dict[str, Any]:
        self.create_collection(collection)
        if not key:
            raise ValueError("Record key is required")

        copied_value = deepcopy(value)
        encoded_value = json.dumps(copied_value, sort_keys=True)
        self._connection.execute(
            """
            INSERT INTO records (collection, record_key, value)
            VALUES (?, ?, ?)
            ON CONFLICT(collection, record_key)
            DO UPDATE SET value = excluded.value
            """,
            (collection, key, encoded_value),
        )
        self._connection.commit()
        return copied_value

    def get(
        self,
        collection: str,
        key: str,
    ) -> dict[str, Any] | None:
        row = self._connection.execute(
            """
            SELECT value FROM records
            WHERE collection = ? AND record_key = ?
            """,
            (collection, key),
        ).fetchone()
        if row is None:
            return None
        return deepcopy(json.loads(row["value"]))

    def delete(self, collection: str, key: str) -> bool:
        cursor = self._connection.execute(
            """
            DELETE FROM records
            WHERE collection = ? AND record_key = ?
            """,
            (collection, key),
        )
        self._connection.commit()
        return cursor.rowcount > 0

    def list_collection(self, collection: str) -> list[dict[str, Any]]:
        rows = self._connection.execute(
            """
            SELECT value FROM records
            WHERE collection = ?
            ORDER BY rowid
            """,
            (collection,),
        ).fetchall()
        return [
            deepcopy(json.loads(row["value"]))
            for row in rows
        ]

    def collections(self) -> list[str]:
        rows = self._connection.execute(
            "SELECT name FROM collections ORDER BY name"
        ).fetchall()
        return [row["name"] for row in rows]

    def health(self) -> dict[str, Any]:
        collection_count = self._connection.execute(
            "SELECT COUNT(*) FROM collections"
        ).fetchone()[0]
        record_count = self._connection.execute(
            "SELECT COUNT(*) FROM records"
        ).fetchone()[0]
        return {
            "status": "ONLINE",
            "collections": int(collection_count),
            "records": int(record_count),
            "durable": self.path != ":memory:",
        }

    def close(self) -> None:
        self._connection.close()
