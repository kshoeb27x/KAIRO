from __future__ import annotations

from dataclasses import dataclass, field, replace
from uuid import uuid4


@dataclass(frozen=True)
class ExecutionContext:
    caller_identity: str
    permission: str
    operation: str
    resource: str
    agent_identity: str | None = None
    authority: int = 0
    requested_capability: str | None = None
    correlation_id: str = field(default_factory=lambda: uuid4().hex)
    origin: str = "internal"
    approval_id: str | None = None
    delegated_by: str | None = None
    metadata: tuple[tuple[str, str], ...] = ()

    def derive(
        self,
        *,
        permission: str | None = None,
        operation: str | None = None,
        resource: str | None = None,
        agent_identity: str | None = None,
        requested_capability: str | None = None,
        delegated_by: str | None = None,
        approval_id: str | None = None,
    ) -> "ExecutionContext":
        return replace(
            self,
            permission=permission or self.permission,
            operation=operation or self.operation,
            resource=resource or self.resource,
            agent_identity=(
                self.agent_identity
                if agent_identity is None
                else agent_identity
            ),
            requested_capability=(
                requested_capability
                if requested_capability is not None
                else self.requested_capability
            ),
            delegated_by=delegated_by or self.delegated_by,
            approval_id=approval_id or self.approval_id,
        )


@dataclass(frozen=True)
class AuthorizationDecision:
    decision: str
    permission: str
    reason: str
    correlation_id: str

    @property
    def allowed(self) -> bool:
        return self.decision == "ALLOW"
