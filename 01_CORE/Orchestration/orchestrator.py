"""KAIRO V1 orchestration layer."""

from __future__ import annotations

from typing import Any

from Context.context import KairoContext
from Planning.planner import KairoPlanner
from Reasoning.reasoner import KairoReasoner
from Manager.agent_manager import AgentManager
from Research.research_agent import ResearchAgent
from Coding.coding_agent import CodingAgent
from Data.data_agent import DataAgent


class KairoOrchestrator:
    """Central dispatcher using context, reasoning, planning and runtime."""

    def __init__(self, runtime: Any) -> None:
        self.runtime = runtime
        self.context = KairoContext()
        self.planner = KairoPlanner()
        self.reasoner = KairoReasoner()
        self.agents = AgentManager()
        self.agents.register(ResearchAgent())
        self.agents.register(CodingAgent())
        self.agents.register(DataAgent())

    def dispatch(self, message: str) -> str:
        context = self.context.build(message)

        result = self.reasoner.analyze(
            context.current_input,
            context.history,
        )

        intent = result.intent

        if intent == "greeting":
            return "Hello. KAIRO V1 is online."

        if intent == "status_request":
            status = self.runtime.status()
            runtime_status = status.get("runtime", status)
            return (
                "KAIRO V1 | "
                f"Core: {status.get('core', 'ONLINE')} | "
                f"Runtime: {runtime_status.get('status', 'ONLINE')} | "
                f"Security: {status.get('security', 'ONLINE')} | "
                f"Tasks: {status.get('tasks', runtime_status.get('tasks', 0))} | "
                f"Events: {status.get('events', runtime_status.get('events', 0))}"
            )

        if intent == "task_creation":
            name = message[len("create task "):].strip()

            if not name:
                return "Task name is required."

            task = self.runtime.create_task(name)
            return f"Task created: {task['name']} [{task['id']}]"

        if intent == "planning_request":
            goal = message[len("plan "):].strip()

            if not goal:
                return "Planning goal is required."

            plan = self.planner.create_plan(goal)
            return f"Plan created: {plan.goal} [{len(plan.steps)} steps]"

        if intent == "research_request":
            task = message[len("research "):].strip()
            if not task:
                return "Research task is required."
            agent_result = self.agents.execute("research", task)
            return agent_result.result

        if intent == "coding_request":
            task = message[len("code "):].strip()
            if not task:
                return "Coding task is required."
            agent_result = self.agents.execute("coding", task)
            return agent_result.result

        if intent == "data_request":
            task = message[len("data "):].strip()
            if not task:
                return "Data task is required."
            agent_result = self.agents.execute("data", task)
            return agent_result.result

        if intent == "general_request":
            return result.reasoning

        if message.lower() in {"exit", "quit"}:
            return "__EXIT__"

        return f"I received: {message}"
