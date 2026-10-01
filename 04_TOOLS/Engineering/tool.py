from __future__ import annotations

from typing import Any

from ..tool import ToolDefinition


class EngineeringTool:
    """Authorized tool-manager facade for Engineering Agent operations."""

    definition = ToolDefinition(
        name="engineering",
        description="Inspect Engineering Agent status or submit an engineering objective.",
        category="Engineering",
        permissions=["tool.invoke"],
    )

    def __init__(self, agent_manager: Any, engineering_agent: Any) -> None:
        self.agent_manager = agent_manager
        self.engineering_agent = engineering_agent

    def execute(
        self,
        action: str,
        arguments: dict[str, Any],
        context: Any | None = None,
    ) -> dict[str, Any]:
        if action == "status":
            return self.engineering_agent.health()
        if action == "run":
            objective = arguments.get("objective")
            if not isinstance(objective, str) or not objective.strip():
                raise ValueError("Engineering objective is required.")
            if context is None:
                raise PermissionError(
                    "Engineering tool execution requires an authorization context."
                )
            result = self.agent_manager.execute(
                "engineering",
                objective,
                context=context,
            )
            return {
                "agent": result.agent,
                "task": result.task,
                "status": result.status,
                "result": result.result,
                "request_id": result.request_id,
            }
        if action == "rollback":
            checkpoint_id = arguments.get("checkpoint_id")
            if not isinstance(checkpoint_id, str) or not checkpoint_id.strip():
                raise ValueError("Engineering checkpoint ID is required.")
            if context is None:
                raise PermissionError(
                    "Engineering rollback requires an authorization context."
                )
            return self.engineering_agent.rollback(
                checkpoint_id,
                context,
            )
        raise ValueError(f"Unsupported engineering action: {action}")
