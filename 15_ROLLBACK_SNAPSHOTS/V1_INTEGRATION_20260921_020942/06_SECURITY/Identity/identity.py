from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any


@dataclass
class Identity:
    identity_id: str
    name: str
    identity_type: str
    active: bool = True
    created_at: str = ""


class IdentityManager:
    """Manages identities known to KAIRO security."""

    def __init__(self) -> None:
        self._identities: dict[str, Identity] = {}

    def create(
        self,
        identity_id: str,
        name: str,
        identity_type: str = "USER",
    ) -> Identity:

        if identity_id in self._identities:
            raise ValueError(
                "Identity already exists"
            )

        identity = Identity(
            identity_id=identity_id,
            name=name,
            identity_type=identity_type,
            created_at=datetime.now().isoformat(),
        )

        self._identities[
            identity_id
        ] = identity

        return identity

    def get(
        self,
        identity_id: str,
    ) -> Identity | None:

        return self._identities.get(
            identity_id
        )

    def deactivate(
        self,
        identity_id: str,
    ) -> bool:

        identity = self.get(identity_id)

        if identity is None:
            return False

        identity.active = False

        return True

    def list_identities(self) -> list[dict[str, Any]]:
        return [
            asdict(identity)
            for identity in self._identities.values()
        ]

    def health(self) -> dict[str, Any]:
        return {
            "status": "ONLINE",
            "count": len(self._identities),
            "active": sum(
                1
                for identity in self._identities.values()
                if identity.active
            ),
        }
