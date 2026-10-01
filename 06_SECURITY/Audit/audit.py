from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
import json
import os
from pathlib import Path
import sqlite3
from typing import Any


@dataclass
class AuditEntry:
    event: str
    identity_id: str | None
    action: str
    status: str
    details: dict[str, Any]
    created_at: str


class AuditLogger:
    """Security audit log with durable SQLite storage and a process-local view."""

    def __init__(self, database_path: str | Path | None = None) -> None:
        self._entries: list[AuditEntry] = []
        default_path = (
            Path(__file__).resolve().parents[2]
            / "03_DATA"
            / "Database"
            / "security_audit.sqlite3"
        )
        self.database_path = Path(
            database_path
            or os.environ.get("KAIRO_AUDIT_DB", default_path)
        )
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.database_path) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS security_audit (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event TEXT NOT NULL,
                    identity_id TEXT,
                    action TEXT NOT NULL,
                    status TEXT NOT NULL,
                    details TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )

    def record(
        self,
        event: str,
        identity_id: str | None,
        action: str,
        status: str,
        details: dict[str, Any] | None = None,
    ) -> AuditEntry:

        entry = AuditEntry(
            event=event,
            identity_id=identity_id,
            action=action,
            status=status,
            details=details or {},
            created_at=datetime.now().isoformat(),
        )

        self._entries.append(entry)
        try:
            with sqlite3.connect(self.database_path) as connection:
                connection.execute(
                    """
                    INSERT INTO security_audit
                        (event, identity_id, action, status, details, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        entry.event,
                        entry.identity_id,
                        entry.action,
                        entry.status,
                        json.dumps(entry.details, sort_keys=True),
                        entry.created_at,
                    ),
                )
        except sqlite3.Error as error:
            self._entries.pop()
            raise RuntimeError("Unable to persist security audit event.") from error

        return entry

    def recent(
        self,
        limit: int = 100,
    ) -> list[dict[str, Any]]:

        return [
            asdict(entry)
            for entry in self._entries[-limit:]
        ]

    def count(self) -> int:
        return len(self._entries)

    def durable_recent(self, limit: int = 100) -> list[dict[str, Any]]:
        if limit <= 0:
            return []
        try:
            with sqlite3.connect(self.database_path) as connection:
                rows = connection.execute(
                    """
                    SELECT event, identity_id, action, status, details, created_at
                    FROM security_audit
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    (limit,),
                ).fetchall()
        except sqlite3.Error as error:
            raise RuntimeError("Unable to read durable security audit events.") from error
        return [
            {
                "event": event,
                "identity_id": identity_id,
                "action": action,
                "status": status,
                "details": json.loads(details),
                "created_at": created_at,
            }
            for event, identity_id, action, status, details, created_at in reversed(rows)
        ]

    def health(self) -> dict[str, Any]:
        return {
            "status": "ONLINE",
            "entries": len(self._entries),
            "durable": True,
        }
