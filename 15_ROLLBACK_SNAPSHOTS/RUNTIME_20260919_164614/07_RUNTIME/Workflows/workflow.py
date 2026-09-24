from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from ..Events.event_bus import EventBus
from ..State.runtime_state import RuntimeState


@dataclass
class WorkflowStep:
    name: str
    function: Callable[..., Any]


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
    ) -> None:
        self.name = name
        self.state = state
        self.events = events
        self.steps: list[WorkflowStep] = []

    def add_step(
        self,
        name: str,
        function: Callable[..., Any],
    ) -> "Workflow":
        self.steps.append(
            WorkflowStep(
                name=name,
                function=function,
            )
        )

        return self

    def run(self) -> WorkflowResult:
        results: list[Any] = []

        self.state.active_workflows += 1

        self.events.emit(
            "WORKFLOW_STARTED",
            {
                "name": self.name,
            },
        )

        try:
            for step in self.steps:
                self.events.emit(
                    "WORKFLOW_STEP_STARTED",
                    {
                        "workflow": self.name,
                        "step": step.name,
                    },
                )

                result = step.function()

                results.append(result)

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
