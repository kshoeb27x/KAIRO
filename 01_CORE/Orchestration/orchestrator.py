"""KAIRO V1 orchestration layer."""

from __future__ import annotations

from typing import Any

from Context.context import KairoContext
from Planning.planner import KairoPlanner
from Reasoning.reasoner import KairoReasoner
from Manager.agent_manager import AgentManager
from AI.ai import KairoAI


class KairoOrchestrator:
    """Central dispatcher using context, reasoning, planning and runtime."""

    def __init__(self, runtime: Any, security: Any | None = None) -> None:
        self.runtime = runtime
        self.context = KairoContext()
        self.planner = KairoPlanner()
        self.reasoner = KairoReasoner(
            ai=KairoAI(security=security),
        )

        self.agents = AgentManager(
            runtime=runtime,
            security=security,
        )

    def dispatch(self, message: str, context: Any | None = None) -> str:
        message = message.strip()

        if not message:
            return "KAIRO received an empty request."

        if message.lower() in {"exit", "quit"}:
            return "__EXIT__"

        conversation_context = self.context.build(message)

        result = self.reasoner.analyze(
            conversation_context.current_input,
            conversation_context.history,
            context,
        )

        intent = result.intent

        if intent == "greeting":
            return "Hello. KAIRO V1 is online."

        if intent == "status_request":
            status = self.runtime.status()

            runtime_status = status.get(
                "runtime",
                status,
            )

            return (
                "KAIRO V1 | "
                f"Core: {status.get('core', 'ONLINE')} | "
                f"Runtime: {runtime_status.get('status', 'ONLINE')} | "
                f"Tasks: {status.get('tasks', runtime_status.get('tasks', 0))} | "
                f"Events: {status.get('events', runtime_status.get('events', 0))}"
            )

        if intent == "task_creation":
            prefix = "create task "

            if message.lower().startswith(prefix):
                name = message[len(prefix):].strip()
            else:
                name = ""

            if not name:
                return "Task name is required."

            task = self.runtime.create_task(name, context)

            return (
                f"Task created: "
                f"{task['name']} [{task['id']}]"
            )

        if intent == "planning_request":
            prefix = "plan "

            if message.lower().startswith(prefix):
                goal = message[len(prefix):].strip()
            else:
                goal = ""

            if not goal:
                return "Planning goal is required."

            plan = self.planner.create_plan(goal)

            return (
                f"Plan created: "
                f"{plan.goal} "
                f"[{len(plan.steps)} steps]"
            )

        if intent == "research_request":
            prefix = "research "

            if message.lower().startswith(prefix):
                task = message[len(prefix):].strip()
            else:
                task = ""

            if not task:
                return "Research task is required."

            if self.agents.get("research") is None:
                return "Research agent is not registered."

            agent_result = self.agents.execute(
                "research",
                task,
                context=context,
            )

            return self._agent_response(agent_result)

        if intent == "coding_request":
            prefix = "code "

            if message.lower().startswith(prefix):
                task = message[len(prefix):].strip()
            else:
                task = ""

            if not task:
                return "Coding task is required."

            if self.agents.get("coding") is None:
                return "Coding agent is not registered."

            agent_result = self.agents.execute(
                "coding",
                task,
                context=context,
            )

            return self._agent_response(agent_result)

        if intent == "data_request":
            prefix = "data "

            if message.lower().startswith(prefix):
                task = message[len(prefix):].strip()
            else:
                task = ""

            if not task:
                return "Data task is required."

            if self.agents.get("data") is None:
                return "Data agent is not registered."

            agent_result = self.agents.execute(
                "data",
                task,
                context=context,
            )

            return self._agent_response(agent_result)

        if intent == "engineering_request":
            if self.agents.get("engineering") is None:
                return "Engineering agent is not registered."
            agent_result = self.agents.execute(
                "engineering",
                message,
                context=context,
            )
            return self._agent_response(agent_result)

        if intent == "general_request":
            return result.reasoning

        return f"I received: {message}"

    @staticmethod
    def _agent_response(agent_result: Any) -> str:
        if agent_result.status == "COMPLETED":
            value = agent_result.result
            if hasattr(value, "result"):
                value = value.result
            return str(value)
        value = agent_result.result
        if hasattr(value, "result"):
            value = value.result
        return f"{agent_result.agent} agent {agent_result.status}: {value}"
