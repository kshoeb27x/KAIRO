from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
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
    """In-process security audit log."""

    def __init__(self) -> None:
        self._entries: list[AuditEntry] = []

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

    def health(self) -> dict[str, Any]:
        return {
            "status": "ONLINE",
            "entries": len(self._entries),
        }
