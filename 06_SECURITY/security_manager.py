from __future__ import annotations

import os
from typing import Any

from .Audit.audit import AuditLogger
from .Authority.authority import (
    AuthorityLevel,
    AuthorityManager,
)
from .Identity.identity import IdentityManager
from .Permissions.permissions import PermissionManager
from .Sandbox.sandbox import SandboxPolicy
from .Sandbox.provider import SandboxProvider
from .Secrets.secrets import SecretStore
from .execution_context import AuthorizationDecision, ExecutionContext
from src.policy import load_policy
from uuid import uuid4


KNOWN_PERMISSIONS = frozenset(
    {
        "agent.execute",
        "agent.delegate",
        "runtime.task.create",
        "runtime.task.read",
        "runtime.execute",
        "runtime.workflow.execute",
        "runtime.schedule",
        "runtime.emergency_stop",
        "tool.invoke",
        "network.read",
        "network.write",
        "automation.execute",
        "computer.interact",
        "mcp.execute",
        "data.read",
        "data.write",
        "model.invoke",
        "model.external",
        "filesystem.read",
        "filesystem.write",
        "process.execute",
        "shell.execute",
        "security.approve",
        "api.status.read",
        "api.tasks.read",
        "api.events.read",
        "api.chat",
        "api.tasks.create",
        "api.agents.execute",
        "api.tools.execute",
        "api.runtime.control",
        "api.workflows.execute",
        "api.memory.read",
        "api.memory.write",
        "engineering.inspect",
        "engineering.plan",
        "engineering.modify",
        "engineering.modify_tests",
        "engineering.test",
        "engineering.checkpoint",
        "engineering.rollback",
    }
)

APPROVAL_PERMISSIONS = frozenset(
    {
        "network.write",
        "computer.interact",
        "filesystem.write",
        "process.execute",
        "shell.execute",
        "model.external",
    }
)


class SecurityManager:
    """Unified KAIRO security control layer."""

    def __init__(self) -> None:

        self.identity = IdentityManager()
        self.authority = AuthorityManager()
        self.permissions = PermissionManager()
        self.secrets = SecretStore()
        self.audit = AuditLogger()

        self.sandbox = SandboxPolicy(
            allow_network=self._environment_flag(
                "KAIRO_SANDBOX_ALLOW_NETWORK"
            ),
            allow_filesystem_write=self._environment_flag(
                "KAIRO_SANDBOX_ALLOW_FILESYSTEM_WRITE"
            ),
            allow_process_execution=self._environment_flag(
                "KAIRO_SANDBOX_ALLOW_PROCESS_EXECUTION"
            ),
            allow_shell=self._environment_flag(
                "KAIRO_SANDBOX_ALLOW_SHELL"
            ),
        )
        self.policy = load_policy()
        self.sandbox_provider = SandboxProvider(
            self.sandbox,
            self.audit,
            self,
        )
        self._approvals: dict[str, tuple[str, str, str, str, str | None, str]] = {}
        self._emergency_stopped = False

    @staticmethod
    def _environment_flag(name: str) -> bool:
        value = os.environ.get(name)
        if value is None:
            return False
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
        raise ValueError(
            f"{name} must be set to a boolean value."
        )

    def context(
        self,
        identity_id: str,
        permission: str,
        operation: str,
        resource: str,
        *,
        agent_identity: str | None = None,
        origin: str = "internal",
        correlation_id: str | None = None,
        approval_id: str | None = None,
        delegated_by: str | None = None,
    ) -> ExecutionContext:
        identity = self.identity.get(identity_id)
        authority = int(self.authority.get(identity_id))
        if identity is None:
            authority = 0
        return ExecutionContext(
            caller_identity=identity_id,
            agent_identity=agent_identity,
            authority=authority,
            permission=permission,
            requested_capability=permission,
            operation=operation,
            resource=resource,
            origin=origin,
            correlation_id=correlation_id or uuid4().hex,
            approval_id=approval_id,
            delegated_by=delegated_by,
        )

    def register_agent(
        self,
        agent_name: str,
        permissions: tuple[str, ...] = (),
    ) -> None:
        identity_id = f"agent:{agent_name}"
        if self.identity.get(identity_id) is None:
            self.identity.create(
                identity_id,
                agent_name,
                "AGENT",
            )
            self.authority.assign(identity_id, AuthorityLevel.USER)
            self.permissions.grant(identity_id, "agent.execute")
            self.permissions.grant(identity_id, "runtime.execute")
        for permission in permissions:
            if permission not in KNOWN_PERMISSIONS:
                raise ValueError(f"Unknown permission: {permission}")
            self.permissions.grant(identity_id, permission)

    def provision_api_identity(
        self,
        identity_id: str,
        permissions: tuple[str, ...],
    ) -> None:
        if self.identity.get(identity_id) is None:
            self.identity.create(identity_id, identity_id, "API")
            self.authority.assign(identity_id, AuthorityLevel.USER)
        for permission in permissions:
            if permission not in KNOWN_PERMISSIONS:
                raise ValueError(f"Unknown permission: {permission}")
            self.permissions.grant(identity_id, permission)

    def authorize(
        self,
        identity_id: str | ExecutionContext,
        permission: str | None = None,
        authority: AuthorityLevel = AuthorityLevel.USER,
    ) -> bool | AuthorizationDecision:
        if isinstance(identity_id, ExecutionContext):
            context = identity_id
            required_permission = permission or context.permission
            return self._authorize_context(context, required_permission, authority)

        if not permission:
            self.audit.record(
                "AUTHORIZATION",
                identity_id,
                "",
                "DENY",
                {"reason": "MISSING_PERMISSION"},
            )
            return False
        context = self.context(
            identity_id,
            permission,
            permission,
            permission,
        )
        return self._authorize_context(
            context,
            permission,
            authority,
        ).allowed

    def authorize_context(
        self,
        context: ExecutionContext,
        permission: str | None = None,
        authority: AuthorityLevel = AuthorityLevel.USER,
    ) -> AuthorizationDecision:
        return self._authorize_context(
            context,
            permission or context.permission,
            authority,
        )

    def _authorize_context(
        self,
        context: ExecutionContext,
        permission: str,
        authority: AuthorityLevel,
    ) -> AuthorizationDecision:
        reason = "ALLOWED"
        decision = "ALLOW"
        identity = self.identity.get(context.caller_identity)

        if (
            self._emergency_stopped
            and permission != "security.approve"
        ):
            decision, reason = "DENY", "EMERGENCY_STOP"
        elif permission not in KNOWN_PERMISSIONS:
            decision, reason = "DENY", "UNKNOWN_PERMISSION"
        elif context.permission != permission:
            decision, reason = "DENY", "CONTEXT_PERMISSION_MISMATCH"
        elif identity is None or not identity.active:
            decision, reason = "DENY", "UNKNOWN_OR_INACTIVE_IDENTITY"
        elif context.authority != int(self.authority.get(context.caller_identity)):
            decision, reason = "DENY", "AUTHORITY_CONTEXT_MISMATCH"
        elif not self.authority.allows(context.caller_identity, authority):
            decision, reason = "DENY", "INSUFFICIENT_AUTHORITY"
        elif not self.permissions.allows(context.caller_identity, permission):
            decision, reason = "DENY", "PERMISSION_NOT_GRANTED"
        elif context.agent_identity:
            agent = self.identity.get(context.agent_identity)
            if agent is None or not agent.active:
                decision, reason = "DENY", "UNKNOWN_OR_INACTIVE_AGENT"
            elif not self.permissions.allows(context.agent_identity, permission):
                decision, reason = "DENY", "AGENT_PERMISSION_NOT_GRANTED"
        if decision == "ALLOW" and context.delegated_by:
            delegator_id = f"agent:{context.delegated_by}"
            delegator = self.identity.get(delegator_id)
            if delegator is None or not delegator.active:
                decision, reason = "DENY", "UNKNOWN_OR_INACTIVE_DELEGATOR"
            elif not self.permissions.allows(delegator_id, permission):
                decision, reason = "DENY", "DELEGATED_PERMISSION_EXCEEDS_DELEGATOR"
        if (
            decision == "ALLOW"
            and permission in APPROVAL_PERMISSIONS
            and self.policy.approval.critical_actions
            and not self._approval_matches(context, permission)
        ):
            decision, reason = "REQUIRES_APPROVAL", "APPROVAL_REQUIRED"

        result = AuthorizationDecision(
            decision=decision,
            permission=permission,
            reason=reason,
            correlation_id=context.correlation_id,
        )
        self.audit.record(
            "AUTHORIZATION",
            context.caller_identity,
            context.operation,
            decision,
            {
                "agent_identity": context.agent_identity,
                "authority": int(
                    self.authority.get(context.caller_identity)
                ),
                "resource": context.resource,
                "permission": permission,
                "reason": reason,
                "correlation_id": context.correlation_id,
                "origin": context.origin,
                "delegated_by": context.delegated_by,
            },
        )
        return result

    def set_emergency_stopped(self, stopped: bool) -> None:
        self._emergency_stopped = stopped

    def _approval_matches(
        self,
        context: ExecutionContext,
        permission: str,
    ) -> bool:
        if not context.approval_id:
            return False
        approved = self._approvals.pop(context.approval_id, None)
        return approved == (
            context.caller_identity,
            permission,
            context.operation,
            context.resource,
            context.agent_identity,
            context.correlation_id,
        )

    def approve(
        self,
        context: ExecutionContext,
        approver_identity: str,
    ) -> str:
        approver = self.context(
            approver_identity,
            "security.approve",
            "approve",
            context.resource,
            origin="approval",
            correlation_id=context.correlation_id,
        )
        decision = self._authorize_context(
            approver,
            "security.approve",
            AuthorityLevel.ADMIN,
        )
        if not decision.allowed:
            raise PermissionError(decision.reason)
        approval_id = uuid4().hex
        self._approvals[approval_id] = (
            context.caller_identity,
            context.permission,
            context.operation,
            context.resource,
            context.agent_identity,
            context.correlation_id,
        )
        self.audit.record(
            "APPROVAL",
            approver_identity,
            context.operation,
            "ALLOWED",
            {
                "resource": context.resource,
                "permission": context.permission,
                "correlation_id": context.correlation_id,
                "approval_id": approval_id,
            },
        )
        return approval_id

    def audit_execution(
        self,
        context: ExecutionContext,
        result: str,
        error: str | None = None,
    ) -> None:
        self.audit.record(
            "EXECUTION",
            context.caller_identity,
            context.operation,
            result,
            {
                "agent_identity": context.agent_identity,
                "resource": context.resource,
                "permission": context.permission,
                "correlation_id": context.correlation_id,
                "origin": context.origin,
                "delegated_by": context.delegated_by,
                "error": "[REDACTED]" if error else None,
            },
        )

    def health(self) -> dict[str, Any]:

        return {
            "status": (
                "EMERGENCY_STOP"
                if self._emergency_stopped
                else "ONLINE"
            ),
            "identity": self.identity.health(),
            "authority": self.authority.health(),
            "permissions": self.permissions.health(),
            "secrets": self.secrets.health(),
            "audit": self.audit.health(),
            "sandbox": self.sandbox.summary(),
            "sandbox_provider": self.sandbox_provider.health(),
        }
