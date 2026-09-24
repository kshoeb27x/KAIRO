from __future__ import annotations

from enum import IntEnum
from typing import Any


class AuthorityLevel(IntEnum):
    GUEST = 0
    USER = 10
    OPERATOR = 20
    ADMIN = 30
    SYSTEM = 40


class AuthorityManager:
    """Controls authority levels for identities."""

    def __init__(self) -> None:
        self._levels: dict[str, AuthorityLevel] = {}

    def assign(
        self,
        identity_id: str,
        level: AuthorityLevel,
    ) -> None:

        self._levels[
            identity_id
        ] = level

    def get(
        self,
        identity_id: str,
    ) -> AuthorityLevel:

        return self._levels.get(
            identity_id,
            AuthorityLevel.GUEST,
        )

    def allows(
        self,
        identity_id: str,
        required: AuthorityLevel,
    ) -> bool:

        return (
            self.get(identity_id)
            >= required
        )

    def health(self) -> dict[str, Any]:
        return {
            "status": "ONLINE",
            "assignments": len(
                self._levels
            ),
        }
