"""KAIRO agent authority and lifecycle control."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import FrozenSet


class AgentState(str, Enum):
    CREATED = "CREATED"
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    STOPPING = "STOPPING"
    STOPPED = "STOPPED"
    TERMINATED = "TERMINATED"


class Permission(str, Enum):
    EXECUTE = "execute"
    READ_DATA = "read_data"
    WRITE_DATA = "write_data"
    USE_TOOLS = "use_tools"
    DELEGATE = "delegate"
    BROWSER = "browser"
    COMPUTER_USE = "computer_use"
    NETWORK = "network"
    MODIFY_SYSTEM = "modify_system"
    ENGINEERING_INSPECT = "engineering_inspect"
    ENGINEERING_PLAN = "engineering_plan"
    ENGINEERING_MODIFY = "engineering_modify"
    ENGINEERING_MODIFY_TESTS = "engineering_modify_tests"
    ENGINEERING_TEST = "engineering_test"
    ENGINEERING_CHECKPOINT = "engineering_checkpoint"
    ENGINEERING_ROLLBACK = "engineering_rollback"
    FILESYSTEM_WRITE = "filesystem_write"
    PROCESS_EXECUTE = "process_execute"
    MODEL_EXTERNAL = "model_external"
    CREATE_TASK = "create_task"


@dataclass(frozen=True)
class AgentAuthority:
    """Immutable authority granted to an agent."""

    agent_name: str
    permissions: FrozenSet[Permission] = field(default_factory=frozenset)
    critical_operations_allowed: bool = False

    def allows(self, permission: Permission) -> bool:
        return permission in self.permissions

    def allows_critical(self) -> bool:
        return self.critical_operations_allowed

    def without(self, permission: Permission) -> "AgentAuthority":
        return AgentAuthority(
            agent_name=self.agent_name,
            permissions=frozenset(
                p for p in self.permissions if p != permission
            ),
            critical_operations_allowed=self.critical_operations_allowed,
        )


@dataclass
class AgentControl:
    """Runtime control state for one registered agent."""

    name: str
    authority: AgentAuthority
    state: AgentState = AgentState.CREATED
    execution_count: int = 0
    failure_count: int = 0
    last_status: str = "NEVER_EXECUTED"

    def can_execute(self) -> bool:
        return (
            self.state == AgentState.RUNNING
            and self.authority.allows(Permission.EXECUTE)
        )


class AuthorityError(PermissionError):
    """Raised when an agent attempts an unauthorized operation."""


class LifecycleError(RuntimeError):
    """Raised when an invalid lifecycle transition is requested."""


class AgentAuthorityController:
    """Controls authority and lifecycle transitions."""

    _TRANSITIONS = {
        AgentState.CREATED: {AgentState.STARTING},
        AgentState.STARTING: {
            AgentState.RUNNING,
            AgentState.STOPPING,
        },
        AgentState.RUNNING: {
            AgentState.PAUSED,
            AgentState.STOPPING,
        },
        AgentState.PAUSED: {
            AgentState.RUNNING,
            AgentState.STOPPING,
        },
        AgentState.STOPPING: {
            AgentState.STOPPED,
        },
        AgentState.STOPPED: {
            AgentState.STARTING,
            AgentState.TERMINATED,
        },
        AgentState.TERMINATED: set(),
    }

    def transition(
        self,
        control: AgentControl,
        target: AgentState,
    ) -> AgentState:
        allowed = self._TRANSITIONS.get(control.state, set())

        if target not in allowed:
            raise LifecycleError(
                f"Invalid lifecycle transition: "
                f"{control.name}: "
                f"{control.state.value} -> {target.value}"
            )

        control.state = target
        return control.state

    def require(
        self,
        control: AgentControl,
        permission: Permission,
    ) -> None:
        if control.state != AgentState.RUNNING:
            raise AuthorityError(
                f"Agent '{control.name}' is not RUNNING "
                f"(current state: {control.state.value})"
            )

        if not control.authority.allows(permission):
            raise AuthorityError(
                f"Agent '{control.name}' is not authorized "
                f"for permission '{permission.value}'"
            )

    def require_critical(
        self,
        control: AgentControl,
    ) -> None:
        self.require(control, Permission.EXECUTE)

        if not control.authority.allows_critical():
            raise AuthorityError(
                f"Agent '{control.name}' is not authorized "
                f"for critical operations"
            )

    def terminate(self, control: AgentControl) -> AgentState:
        if control.state != AgentState.STOPPED:
            raise LifecycleError(
                f"Agent '{control.name}' must be STOPPED before termination "
                f"(current state: {control.state.value})"
            )

        return self.transition(control, AgentState.TERMINATED)

    def revoke_execute(self, control: AgentControl) -> None:
        control.authority = control.authority.without(
            Permission.EXECUTE
        )