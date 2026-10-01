from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from typing import Any, Callable

from ..Events.event_bus import EventBus
from ..State.runtime_state import RuntimeState


@dataclass
class WorkflowStep:
    name: str
    function: Callable[..., Any]
    permission: str


@dataclass
class WorkflowResult:
    name: str
    status: str
    results: list[Any] = field(
        default_factory=list
    )
    error: str | None = None


class Workflow:
    """Sequential workflow executor."""

    def __init__(
        self,
        name: str,
        state: RuntimeState,
        events: EventBus,
        security: Any | None = None,
        context: Any | None = None,
        should_stop: Callable[[], bool] | None = None,
    ) -> None:

        self.name = name
        self.state = state
        self.events = events
        self.security = security
        self.context = context
        self.should_stop = should_stop
        self.steps: list[WorkflowStep] = []

    def add_step(
        self,
        name: str,
        function: Callable[..., Any],
        permission: str = "runtime.execute",
    ) -> "Workflow":

        self.steps.append(
            WorkflowStep(
                name=name,
                function=function,
                permission=permission,
            )
        )

        return self

    def run(self) -> WorkflowResult:

        results: list[Any] = []
        workflow_context = None

        self.state.active_workflows += 1

        self.events.emit(
            "WORKFLOW_STARTED",
            {
                "name": self.name,
            },
        )

        try:
            if self.context is None or self.security is None:
                raise PermissionError(
                    "Workflow execution context and security manager are required."
                )
            workflow_context = self.context.derive(
                permission="runtime.workflow.execute",
                operation="workflow.execute",
                resource=self.name,
            )
            workflow_decision = self.security.authorize_context(
                workflow_context,
                "runtime.workflow.execute",
            )
            if not workflow_decision.allowed:
                self.security.audit_execution(
                    workflow_context,
                    workflow_decision.decision,
                    workflow_decision.reason,
                )
                raise PermissionError(
                    f"Workflow execution denied: {workflow_decision.reason}"
                )

            for step in self.steps:
                if self.should_stop is not None and self.should_stop():
                    raise PermissionError(
                        "Workflow cancelled by emergency stop."
                    )
                if self.context is None or self.security is None:
                    raise PermissionError(
                        "Workflow execution context and security manager are required."
                    )
                step_context = self.context.derive(
                    permission=step.permission,
                    operation="workflow.step",
                    resource=f"{self.name}:{step.name}",
                )
                decision = self.security.authorize_context(
                    step_context,
                    step.permission,
                )
                if not decision.allowed:
                    self.security.audit_execution(
                        step_context,
                        decision.decision,
                        decision.reason,
                    )
                    raise PermissionError(
                        f"Workflow step denied: {step.name}: {decision.reason}"
                    )

                self.events.emit(
                    "WORKFLOW_STEP_STARTED",
                    {
                        "workflow": self.name,
                        "step": step.name,
                    },
                )

                parameters = inspect.signature(step.function).parameters
                accepts_context = (
                    "context" in parameters
                    or any(
                        parameter.kind == inspect.Parameter.VAR_KEYWORD
                        for parameter in parameters.values()
                    )
                )
                result = (
                    step.function(context=step_context)
                    if accepts_context
                    else step.function()
                )

                results.append(result)
                self.security.audit_execution(
                    step_context,
                    "COMPLETED",
                )

                self.events.emit(
                    "WORKFLOW_STEP_COMPLETED",
                    {
                        "workflow": self.name,
                        "step": step.name,
                    },
                )

            self.state.active_workflows = max(
                0,
                self.state.active_workflows - 1,
            )

            self.state.completed_workflows += 1

            self.security.audit_execution(
                workflow_context,
                "COMPLETED",
            )
            self.events.emit(
                "WORKFLOW_COMPLETED",
                {
                    "name": self.name,
                },
            )

            return WorkflowResult(
                name=self.name,
                status="COMPLETED",
                results=results,
            )

        except Exception as exc:

            if self.security is not None and workflow_context is not None:
                self.security.audit_execution(
                    workflow_context,
                    "FAILED",
                    str(exc),
                )
            elif self.security is not None:
                self.security.audit.record(
                    "AUTHORIZATION",
                    None,
                    "workflow.execute",
                    "DENY",
                    {
                        "resource": self.name,
                        "reason": "MISSING_CONTEXT",
                    },
                )

            self.state.active_workflows = max(
                0,
                self.state.active_workflows - 1,
            )

            self.state.failed_workflows += 1

            self.events.emit(
                "WORKFLOW_FAILED",
                {
                    "name": self.name,
                    "error": str(exc),
                },
            )

            return WorkflowResult(
                name=self.name,
                status="FAILED",
                results=results,
                error=str(exc),
            )
