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
        security: Any | None = None,
    ) -> None:
        self.policy = policy or SandboxPolicy()
        self.audit = audit
        self.security = security
        self._operations = 0

    def execute(
        self,
        request: SandboxRequest,
        operation: Callable[[], Any],
        context: Any | None = None,
    ) -> Any:
        permission = {
            "network": "network.write",
            "filesystem_write": "filesystem.write",
            "process_execution": "process.execute",
            "shell": "shell.execute",
        }.get(request.capability)
        if (
            self.security is None
            or context is None
            or permission is None
        ):
            self._record(request, "DENIED", "AUTHORIZATION_CONTEXT_REQUIRED")
            raise PermissionError("Sandbox operation requires security authorization.")

        operation_context = context.derive(
            permission=permission,
            operation=f"sandbox.{request.operation}",
            resource=context.resource,
            requested_capability=request.capability,
        )
        decision = self.security.authorize_context(
            operation_context,
            permission,
        )
        if not decision.allowed:
            self.security.audit_execution(
                operation_context,
                decision.decision,
                decision.reason,
            )
            self._record(request, "DENIED", decision.reason)
            raise PermissionError(
                f"Sandbox operation denied: {decision.reason}"
            )
        if not self.policy.allows(request.capability):
            self.security.audit_execution(
                operation_context,
                "DENIED",
                "CAPABILITY_DISABLED",
            )
            self._record(request, "DENIED", "CAPABILITY_DISABLED")
            raise PermissionError(
                f"Sandbox capability is disabled: {request.capability}"
            )
        self._operations += 1
        try:
            result = operation()
            self.security.audit_execution(operation_context, "COMPLETED")
            self._record(request, "ALLOWED", None)
            return result
        except Exception as error:
            self.security.audit_execution(
                operation_context,
                "FAILED",
                str(error),
            )
            self._record(request, "FAILED", str(error))
            raise

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
