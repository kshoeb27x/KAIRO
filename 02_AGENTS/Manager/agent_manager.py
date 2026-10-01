"""KAIRO V1 agent control plane."""

from __future__ import annotations

import inspect
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

    def __init__(
        self,
        runtime: Any | None = None,
        security: Any | None = None,
    ) -> None:
        self._agents: dict[str, Any] = {}
        self._controls: dict[str, AgentControl] = {}
        self._history: list[AgentExecutionResult] = []
        self._system_killed = False

        self.executor = AgentExecutor()
        self.authority_controller = AgentAuthorityController()
        self.runtime = runtime
        self.security = security

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
        if self.security is not None:
            security_permissions = ["agent.execute", "runtime.execute"]
            permission_mapping = {
                Permission.DELEGATE: "agent.delegate",
                Permission.READ_DATA: "data.read",
                Permission.WRITE_DATA: "data.write",
                Permission.USE_TOOLS: "tool.invoke",
                Permission.BROWSER: "network.read",
                Permission.COMPUTER_USE: "computer.interact",
                Permission.NETWORK: "network.read",
                Permission.ENGINEERING_INSPECT: "engineering.inspect",
                Permission.ENGINEERING_PLAN: "engineering.plan",
                Permission.ENGINEERING_MODIFY: "engineering.modify",
                Permission.ENGINEERING_MODIFY_TESTS: "engineering.modify_tests",
                Permission.ENGINEERING_TEST: "engineering.test",
                Permission.ENGINEERING_CHECKPOINT: "engineering.checkpoint",
                Permission.ENGINEERING_ROLLBACK: "engineering.rollback",
                Permission.FILESYSTEM_WRITE: "filesystem.write",
                Permission.PROCESS_EXECUTE: "process.execute",
                Permission.MODEL_EXTERNAL: "model.external",
                Permission.CREATE_TASK: "runtime.task.create",
            }
            security_permissions.extend(
                permission_mapping[permission]
                for permission in authority.permissions
                if permission in permission_mapping
            )
            self.security.register_agent(
                name,
                tuple(security_permissions),
            )

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
        context: Any | None = None,
    ) -> AgentExecutionResult:

        if self._system_killed:
            if self.security is not None:
                if context is None:
                    self.security.audit.record(
                        "AUTHORIZATION",
                        None,
                        "agent.execute",
                        "DENY",
                        {"agent": name, "reason": "EMERGENCY_STOP"},
                    )
                else:
                    self.security.audit_execution(
                        context.derive(
                            operation="agent.execute",
                            resource=name,
                        ),
                        "DENY",
                        "EMERGENCY_STOP",
                    )
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

        if context is None or self.security is None:
            if self.security is not None:
                self.security.audit.record(
                    "AUTHORIZATION",
                    None,
                    "agent.execute",
                    "DENY",
                    {
                        "agent_identity": f"agent:{agent_name}",
                        "permission": "agent.execute",
                        "resource": agent_name,
                        "reason": "MISSING_CONTEXT_OR_SECURITY",
                    },
                )
            self._emit(
                "AGENT_EXECUTION_DENIED",
                agent_name,
                {"reason": "MISSING_CONTEXT_OR_SECURITY"},
            )
            raise PermissionError(
                "Agent execution requires an authorization context."
            )

        agent_context = context.derive(
            permission="agent.execute",
            operation="agent.execute",
            resource=agent_name,
            agent_identity=f"agent:{agent_name}",
        )
        decision = self.security.authorize_context(
            agent_context,
            "agent.execute",
        )
        if not decision.allowed:
            self.security.audit_execution(
                agent_context,
                decision.decision,
                decision.reason,
            )
            raise PermissionError(
                f"Agent execution denied: {decision.reason}"
            )
        try:
            self.authority_controller.require(
                control,
                Permission.EXECUTE,
            )
        except PermissionError as error:
            self.security.audit_execution(
                agent_context,
                "DENY",
                str(error),
            )
            raise

        request = AgentRequest(
            agent=agent_name,
            task=task,
            context=agent_context,
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
                self._invoke_agent,
                agent,
                task,
                agent_context,
                max_attempts=max_attempts,
                context=agent_context.derive(
                    permission="runtime.execute",
                    operation="agent.runtime.execute",
                    resource=agent_name,
                ),
            )

            result = AgentExecutionResult(
                agent=agent_name,
                task=task,
                status=(
                    getattr(runtime_result.result, "status")
                    if runtime_result.status == "COMPLETED"
                    and hasattr(runtime_result.result, "status")
                    else runtime_result.result.get("status")
                    if runtime_result.status == "COMPLETED"
                    and isinstance(runtime_result.result, dict)
                    and isinstance(runtime_result.result.get("status"), str)
                    else runtime_result.status
                ),
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
        self.security.audit_execution(
            agent_context,
            result.status,
            (
                result.result
                if result.status != "COMPLETED"
                else None
            ),
        )

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

    @staticmethod
    def _invoke_agent(
        agent: Any,
        task: str,
        context: Any,
    ) -> Any:
        parameters = inspect.signature(agent.execute).parameters
        accepts_context = (
            "context" in parameters
            or any(
                parameter.kind == inspect.Parameter.VAR_KEYWORD
                for parameter in parameters.values()
            )
        )
        return (
            agent.execute(task, context=context)
            if accepts_context
            else agent.execute(task)
        )

    def delegate(
        self,
        source_agent: str,
        target_agent: str,
        task: str,
        context: Any | None = None,
    ) -> AgentExecutionResult:
        if context is None or self.security is None:
            raise PermissionError("Delegation requires an authorization context.")
        source_name = source_agent.strip()
        target_name = target_agent.strip()
        source_control = self.control(source_name)
        self.authority_controller.require(
            source_control,
            Permission.DELEGATE,
        )
        if context.agent_identity != f"agent:{source_name}":
            raise PermissionError("Delegator identity does not match the source agent.")
        delegation_context = context.derive(
            permission="agent.delegate",
            operation="agent.delegate",
            resource=target_name,
        )
        decision = self.security.authorize_context(
            delegation_context,
            "agent.delegate",
        )
        if not decision.allowed:
            self.security.audit_execution(
                delegation_context,
                decision.decision,
                decision.reason,
            )
            raise PermissionError(f"Agent delegation denied: {decision.reason}")
        delegated_context = context.derive(
            permission="agent.execute",
            operation="agent.delegated_execute",
            resource=target_name,
            agent_identity=f"agent:{target_name}",
            delegated_by=source_name,
        )
        return self.execute(
            target_name,
            task,
            context=delegated_context,
        )

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
        unavailable = any(
            self._controls[name].last_status == "UNAVAILABLE"
            for name in agents
        )
        status = (
            "EMERGENCY_STOP"
            if self._system_killed
            else "DEGRADED"
            if failures or unavailable
            else "ONLINE"
        )

        return {
            "status": status,
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