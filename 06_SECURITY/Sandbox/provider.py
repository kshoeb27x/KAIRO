from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from ..Audit.audit import AuditLogger
from .sandbox import SandboxPolicy


@dataclass(frozen=True)
class SandboxRequest:
    operation: str
    capability: str
    approved: bool = False


class SandboxProvider:
    """Approval-controlled execution boundary for optional providers."""

    def __init__(
        self,
        policy: SandboxPolicy | None = None,
        audit: AuditLogger | None = None,
    ) -> None:
        self.policy = policy or SandboxPolicy()
        self.audit = audit
        self._operations = 0

    def execute(
        self,
        request: SandboxRequest,
        operation: Callable[[], Any],
    ) -> Any:
        if not request.approved:
            self._record(request, "DENIED", "EXPLICIT_APPROVAL_REQUIRED")
            raise PermissionError("Sandbox operation requires explicit approval.")
        if not self.policy.allows(request.capability):
            self._record(request, "DENIED", "CAPABILITY_DISABLED")
            raise PermissionError(
                f"Sandbox capability is disabled: {request.capability}"
            )
        self._operations += 1
        result = operation()
        self._record(request, "ALLOWED", None)
        return result

    def _record(
        self,
        request: SandboxRequest,
        status: str,
        reason: str | None,
    ) -> None:
        if self.audit is None:
            return
        details = {"capability": request.capability}
        if reason is not None:
            details["reason"] = reason
        self.audit.record(
            "SANDBOX",
            None,
            request.operation,
            status,
            details,
        )

    def health(self) -> dict[str, Any]:
        return {
            "status": "ONLINE",
            "operations": self._operations,
            "policy": self.policy.summary(),
        }
