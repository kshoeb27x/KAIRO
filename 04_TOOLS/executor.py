from __future__ import annotations

import inspect
from typing import Any

from .tool import ToolRequest, ToolResult


class ToolExecutor:
    """Executes tools through one controlled boundary."""

    def __init__(self, registry: Any, security: Any | None = None) -> None:
        self.registry = registry
        self.security = security

    def execute(
        self,
        request: ToolRequest,
        context: Any | None = None,
    ) -> ToolResult:
        context = context or request.context

        tool = self.registry.get(
            request.tool
        )

        if tool is None:
            if self.security is not None:
                if context is None:
                    self.security.audit.record(
                        "AUTHORIZATION",
                        None,
                        f"tool.{request.tool}.{request.action}",
                        "DENY",
                        {
                            "permission": "tool.invoke",
                            "resource": request.tool,
                            "reason": "MISSING_CONTEXT",
                        },
                    )
                else:
                    self.security.audit_execution(
                        context.derive(
                            operation=f"tool.{request.tool}.{request.action}",
                            resource=request.tool,
                        ),
                        "DENY",
                        "TOOL_NOT_REGISTERED",
                    )
            return ToolResult(
                tool=request.tool,
                action=request.action,
                status="FAILED",
                result=None,
                error="Tool not registered",
            )

        definition = tool.definition

        if not definition.enabled:
            if self.security is not None:
                if context is None:
                    self.security.audit.record(
                        "AUTHORIZATION",
                        None,
                        f"tool.{request.tool}.{request.action}",
                        "DENY",
                        {
                            "permission": "tool.invoke",
                            "resource": request.tool,
                            "reason": "MISSING_CONTEXT",
                        },
                    )
                else:
                    self.security.audit_execution(
                        context.derive(
                            operation=f"tool.{request.tool}.{request.action}",
                            resource=request.tool,
                        ),
                        "DENY",
                        "TOOL_DISABLED",
                    )
            return ToolResult(
                tool=request.tool,
                action=request.action,
                status="FAILED",
                result=None,
                error="Tool disabled",
            )

        if self.security is None or context is None:
            error = "Execution context and security manager are required."
            if self.security is not None:
                self.security.audit.record(
                    "AUTHORIZATION",
                    None,
                    f"tool.{request.tool}.{request.action}",
                    "DENY",
                    {
                        "permission": "tool.invoke",
                        "resource": request.tool,
                        "reason": "MISSING_CONTEXT",
                    },
                )
            return ToolResult(
                tool=request.tool,
                action=request.action,
                status="DENIED",
                result=None,
                error=error,
            )

        permissions = definition.permissions or ["tool.invoke"]
        authorized_context = context
        for permission in permissions:
            operation_context = context.derive(
                permission=permission,
                operation=f"tool.{request.tool}.{request.action}",
                resource=request.tool,
                requested_capability=permission,
            )
            decision = self.security.authorize_context(
                operation_context,
                permission,
            )
            if not decision.allowed:
                self.security.audit_execution(
                    operation_context,
                    "DENIED",
                    decision.reason,
                )
                return ToolResult(
                    tool=request.tool,
                    action=request.action,
                    status="DENIED",
                    result=None,
                    error=decision.reason,
                )
            authorized_context = operation_context

        try:
            try:
                execute_parameters = inspect.signature(
                    tool.execute
                ).parameters
            except (TypeError, ValueError):
                execute_parameters = {}
            accepts_context = (
                "context" in execute_parameters
                or any(
                    parameter.kind == inspect.Parameter.VAR_KEYWORD
                    for parameter in execute_parameters.values()
                )
            )
            result = (
                tool.execute(
                    request.action,
                    request.arguments,
                    context=authorized_context,
                )
                if accepts_context
                else tool.execute(
                    request.action,
                    request.arguments,
                )
            )

            self.security.audit_execution(
                operation_context,
                "COMPLETED",
            )
            return ToolResult(
                tool=request.tool,
                action=request.action,
                status="COMPLETED",
                result=result,
            )

        except Exception as exc:
            self.security.audit_execution(
                operation_context,
                "FAILED",
                str(exc),
            )
            return ToolResult(
                tool=request.tool,
                action=request.action,
                status="FAILED",
                result=None,
                error=str(exc),
            )
