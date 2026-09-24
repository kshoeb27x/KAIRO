from __future__ import annotations

from typing import Any

from .Audit.audit import AuditLogger
from .Authority.authority import (
    AuthorityLevel,
    AuthorityManager,
)
from .Identity.identity import IdentityManager
from .Permissions.permissions import PermissionManager
from .Sandbox.sandbox import SandboxPolicy
from .Secrets.secrets import SecretStore


class SecurityManager:
    """Unified KAIRO security control layer."""

    def __init__(self) -> None:

        self.identity = IdentityManager()
        self.authority = AuthorityManager()
        self.permissions = PermissionManager()
        self.secrets = SecretStore()
        self.audit = AuditLogger()

        self.sandbox = SandboxPolicy()

    def authorize(
        self,
        identity_id: str,
        permission: str,
        authority: AuthorityLevel = AuthorityLevel.USER,
    ) -> bool:

        identity = self.identity.get(
            identity_id
        )

        if identity is None:
            self.audit.record(
                "AUTHORIZATION",
                identity_id,
                permission,
                "DENIED",
                {
                    "reason": "UNKNOWN_IDENTITY"
                },
            )

            return False

        if not identity.active:
            self.audit.record(
                "AUTHORIZATION",
                identity_id,
                permission,
                "DENIED",
                {
                    "reason": "INACTIVE_IDENTITY"
                },
            )

            return False

        if not self.authority.allows(
            identity_id,
            authority,
        ):
            self.audit.record(
                "AUTHORIZATION",
                identity_id,
                permission,
                "DENIED",
                {
                    "reason": "INSUFFICIENT_AUTHORITY"
                },
            )

            return False

        if not self.permissions.allows(
            identity_id,
            permission,
        ):
            self.audit.record(
                "AUTHORIZATION",
                identity_id,
                permission,
                "DENIED",
                {
                    "reason": "PERMISSION_NOT_GRANTED"
                },
            )

            return False

        self.audit.record(
            "AUTHORIZATION",
            identity_id,
            permission,
            "ALLOWED",
        )

        return True

    def health(self) -> dict[str, Any]:

        return {
            "status": "ONLINE",
            "identity": self.identity.health(),
            "authority": self.authority.health(),
            "permissions": self.permissions.health(),
            "secrets": self.secrets.health(),
            "audit": self.audit.health(),
            "sandbox": self.sandbox.summary(),
        }
