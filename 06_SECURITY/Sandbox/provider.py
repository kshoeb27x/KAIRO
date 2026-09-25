from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .sandbox import SandboxPolicy


@dataclass(frozen=True)
class SandboxRequest:
    operation: str
    capability: str
    approved: bool = False


class SandboxProvider:
    """Approval-controlled execution boundary for optional providers."""

    def __init__(self, policy: SandboxPolicy | None = None) -> None:
        self.policy = policy or SandboxPolicy()
        self._operations = 0

    def execute(
        self,
        request: SandboxRequest,
        operation: Callable[[], Any],
    ) -> Any:
        if not request.approved:
            raise PermissionError("Sandbox operation requires explicit approval.")
        if not self.policy.allows(request.capability):
            raise PermissionError(
                f"Sandbox capability is disabled: {request.capability}"
            )
        self._operations += 1
        return operation()

    def health(self) -> dict[str, Any]:
        return {
            "status": "ONLINE",
            "operations": self._operations,
            "policy": self.policy.summary(),
        }
