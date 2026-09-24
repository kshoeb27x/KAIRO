"""KAIRO V1 planning layer."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Plan:
    goal: str
    steps: list[str] = field(default_factory=list)
    status: str = "READY"


class KairoPlanner:
    """Creates simple executable plans from structured goals."""

    def create_plan(self, goal: str, steps: list[str] | None = None) -> Plan:
        goal = goal.strip()

        if not goal:
            raise ValueError("Planning goal is required.")

        normalized_steps = [
            step.strip()
            for step in (steps or [])
            if step.strip()
        ]

        return Plan(
            goal=goal,
            steps=normalized_steps,
        )

    def add_step(self, plan: Plan, step: str) -> Plan:
        step = step.strip()

        if not step:
            raise ValueError("Plan step is required.")

        plan.steps.append(step)
        return plan

    def summary(self, plan: Plan) -> dict:
        return {
            "goal": plan.goal,
            "steps": plan.steps,
            "step_count": len(plan.steps),
            "status": plan.status,
        }
