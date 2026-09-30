"""KAIRO V1 agent control plane."""

from __future__ import annotations

from typing import Any

try:
    from ..execution import (
        AgentExecutor,
        AgentExecutionResult,
        AgentRequest,
    )
    from ..authority import (
        AgentAuthority,
        AgentAuthorityController,
        AgentControl,
        AgentState,
        Permission,
    )
except ImportError:
    from execution import (
        AgentExecutor,
        AgentExecutionResult,
        AgentRequest,
    )
    from authority import (
        AgentAuthority,
        AgentAuthorityController,
        AgentControl,
        AgentState,
        Permission,
    )


class AgentManager:
    """Central control plane for KAIRO agents."""

    def __init__(self, runtime: Any | None = None) -> None:
        self._agents: dict[str, Any] = {}
        self._controls: dict[str, AgentControl] = {}
        self._history: list[AgentExecutionResult] = []
        self._system_killed = False

        self.executor = AgentExecutor()
        self.authority_controller = AgentAuthorityController()
        self.runtime = runtime

    def register(
        self,
        agent: Any,
        authority: AgentAuthority | None = None,
    ) -> None:
        name = getattr(agent, "name", "").strip()

        if not name:
            raise ValueError("Agent name is required.")

        if name in self._agents:
            raise ValueError(
                f"Agent already registered: {name}"
            )

        if authority is None:
            authority = AgentAuthority(
                agent_name=name,
                permissions=frozenset({
                    Permission.EXECUTE
                }),
            )

        if authority.agent_name != name:
            raise ValueError(
                "Authority agent name must match "
                "registered agent name."
            )

        self._agents[name] = agent

        control = AgentControl(
            name=name,
            authority=authority,
        )

        self._controls[name] = control

        self.authority_controller.transition(
            control,
            AgentState.STARTING,
        )

        self.authority_controller.transition(
            control,
            AgentState.RUNNING,
        )

        self._emit(
            "AGENT_REGISTERED",
            name,
            {
                "state": control.state.value,
            },
        )

    def get(self, name: str) -> Any | None:
        return self._agents.get(name.strip())

    def control(self, name: str) -> AgentControl:
        control = self._controls.get(name.strip())

        if control is None:
            raise ValueError(
                f"Agent not found: {name}"
            )

        return control

    def list_agents(self) -> list[str]:
        return sorted(self._agents)

    def start(self, name: str) -> AgentState:
        if self._system_killed:
            raise RuntimeError(
                "KAIRO agent system is in EMERGENCY STOP."
            )

        control = self.control(name)

        self.authority_controller.transition(
            control,
            AgentState.STARTING,
        )

        state = self.authority_controller.transition(
            control,
            AgentState.RUNNING,
        )

        self._emit(
            "AGENT_STARTED",
            control.name,
            {
                "state": state.value,
            },
        )

        return state

    def pause(self, name: str) -> AgentState:
        control = self.control(name)

        state = self.authority_controller.transition(
            control,
            AgentState.PAUSED,
        )

        self._emit(
            "AGENT_PAUSED",
            control.name,
            {
                "state": state.value,
            },
        )

        return state

    def resume(self, name: str) -> AgentState:
        if self._system_killed:
            raise RuntimeError(
                "KAIRO agent system is in EMERGENCY STOP."
            )

        control = self.control(name)

        state = self.authority_controller.transition(
            control,
            AgentState.RUNNING,
        )

        self._emit(
            "AGENT_RESUMED",
            control.name,
            {
                "state": state.value,
            },
        )

        return state

    def stop(self, name: str) -> AgentState:
        control = self.control(name)

        if control.state in {
            AgentState.RUNNING,
            AgentState.PAUSED,
            AgentState.STARTING,
        }:
            self.authority_controller.transition(
                control,
                AgentState.STOPPING,
            )

        if control.state == AgentState.STOPPING:
            state = self.authority_controller.transition(
                control,
                AgentState.STOPPED,
            )
        else:
            state = control.state

        self._emit(
            "AGENT_STOPPED",
            control.name,
            {
                "state": state.value,
            },
        )

        return state

    def terminate(self, name: str) -> AgentState:
        control = self.control(name)

        if control.state in {
            AgentState.RUNNING,
            AgentState.PAUSED,
            AgentState.STARTING,
        }:
            self.stop(name)

        self.authority_controller.revoke_execute(
            control
        )

        state = self.authority_controller.terminate(
            control
        )

        self._emit(
            "AGENT_TERMINATED",
            control.name,
            {
                "state": state.value,
            },
        )

        return state

    def emergency_stop(self) -> dict[str, str]:
        self._system_killed = True

        results: dict[str, str] = {}

        for name in self.list_agents():
            control = self._controls[name]

            if control.state in {
                AgentState.RUNNING,
                AgentState.PAUSED,
                AgentState.STARTING,
            }:
                self.stop(name)

            if control.state == AgentState.STOPPED:
                self.authority_controller.revoke_execute(
                    control
                )

            results[name] = control.state.value

        self._emit(
            "AGENT_SYSTEM_EMERGENCY_STOP",
            "SYSTEM",
            {
                "agents": results,
            },
        )

        return results

    def emergency_reset(self) -> None:
        self._system_killed = False

        self._emit(
            "AGENT_SYSTEM_EMERGENCY_RESET",
            "SYSTEM",
            {},
        )

    def execute(
        self,
        name: str,
        task: str,
        max_attempts: int = 1,
    ) -> AgentExecutionResult:

        if self._system_killed:
            raise RuntimeError(
                "KAIRO agent system is in EMERGENCY STOP."
            )

        agent_name = name.strip()
        agent = self.get(agent_name)

        if agent is None:
            raise ValueError(
                f"Agent not found: {name}"
            )

        control = self.control(agent_name)

        self.authority_controller.require(
            control,
            Permission.EXECUTE,
        )

        request = AgentRequest(
            agent=agent_name,
            task=task,
        )

        self._emit(
            "AGENT_EXECUTION_STARTED",
            agent_name,
            {
                "task": task,
                "max_attempts": max_attempts,
            },
        )

        if self.runtime is not None:
            runtime_result = self.runtime.execute(
                f"agent:{agent_name}",
                agent.execute,
                task,
                max_attempts=max_attempts,
            )

            result = AgentExecutionResult(
                agent=agent_name,
                task=task,
                status=runtime_result.status,
                result=(
                    runtime_result.result
                    if runtime_result.status == "COMPLETED"
                    else runtime_result.error
                ),
                started_at=runtime_result.started_at,
                completed_at=runtime_result.completed_at,
                request_id=request.request_id,
            )

        else:
            result = self.executor.execute(
                agent,
                request,
            )

        control.execution_count += 1
        control.last_status = result.status

        if result.status == "FAILED":
            control.failure_count += 1

        self._history.append(result)

        self._emit(
            "AGENT_EXECUTION_COMPLETED",
            agent_name,
            {
                "status": result.status,
                "task": task,
                "request_id": result.request_id,
            },
        )

        return result

    def revoke_execute(self, name: str) -> None:
        control = self.control(name)

        self.authority_controller.revoke_execute(
            control
        )

        self._emit(
            "AGENT_EXECUTE_REVOKED",
            control.name,
            {},
        )

    def history(self) -> list[AgentExecutionResult]:
        return list(self._history)

    def health(self) -> dict[str, Any]:
        agents = self.list_agents()

        failures = sum(
            self._controls[name].failure_count
            for name in agents
        )

        return {
            "status": (
                "EMERGENCY_STOP"
                if self._system_killed
                else "ONLINE"
            ),
            "count": len(agents),
            "failures": failures,
            "agents": agents,
            "states": {
                name: self._controls[name].state.value
                for name in agents
            },
            "execution_counts": {
                name: self._controls[name].execution_count
                for name in agents
            },
            "last_status": {
                name: self._controls[name].last_status
                for name in agents
            },
            "runtime_connected": (
                self.runtime is not None
            ),
        }

    def _emit(
        self,
        event: str,
        source: str,
        data: dict[str, Any],
    ) -> None:
        if self.runtime is None:
            return

        events = getattr(
            self.runtime,
            "events",
            None,
        )

        if events is None:
            return

        events.emit(
            event,
            source,
            data,
        )