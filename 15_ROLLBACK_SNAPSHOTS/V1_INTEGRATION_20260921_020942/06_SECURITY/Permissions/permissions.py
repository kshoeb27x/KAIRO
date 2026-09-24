from __future__ import annotations

from typing import Any


class PermissionManager:
    """Manages explicit permissions for identities."""

    def __init__(self) -> None:
        self._permissions: dict[
            str,
            set[str],
        ] = {}

    def grant(
        self,
        identity_id: str,
        permission: str,
    ) -> None:

        self._permissions.setdefault(
            identity_id,
            set(),
        ).add(permission)

    def revoke(
        self,
        identity_id: str,
        permission: str,
    ) -> bool:

        permissions = self._permissions.get(
            identity_id
        )

        if not permissions:
            return False

        if permission not in permissions:
            return False

        permissions.remove(permission)

        return True

    def allows(
        self,
        identity_id: str,
        permission: str,
    ) -> bool:

        return permission in (
            self._permissions.get(
                identity_id,
                set(),
            )
        )

    def list_permissions(
        self,
        identity_id: str,
    ) -> list[str]:

        return sorted(
            self._permissions.get(
                identity_id,
                set(),
            )
        )

    def health(self) -> dict[str, Any]:
        return {
            "status": "ONLINE",
            "identities": len(
                self._permissions
            ),
            "permissions": sum(
                len(value)
                for value in self._permissions.values()
            ),
        }
