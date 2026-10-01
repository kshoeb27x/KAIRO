from __future__ import annotations

from datetime import datetime
from importlib import import_module
import hmac
import os
from pathlib import Path
import sys
from typing import Any

from src.core.kairo_core import KairoCore
from src.integration import load_components
from src.policy import KairoConfig


AGENTS_ROOT = Path(__file__).resolve().parents[1] / "02_AGENTS"
sys.path.insert(0, str(AGENTS_ROOT))

CodingAgent = import_module("Coding.coding_agent").CodingAgent
DataAgent = import_module("Data.data_agent").DataAgent
EngineeringAgent = import_module(
    "Engineering.engineering_agent"
).EngineeringAgent
ResearchAgent = import_module("Research.research_agent").ResearchAgent

APITool = import_module("04_TOOLS.API.tool").APITool
AutomationTool = import_module("04_TOOLS.Automation.tool").AutomationTool
BrowserTool = import_module("04_TOOLS.Browser.tool").BrowserTool
ComputerUseTool = import_module("04_TOOLS.Computer_Use.tool").ComputerUseTool
MCPTool = import_module("04_TOOLS.MCP.tool").MCPTool


class KairoSystem:
    """Unified KAIRO V1 system composition layer."""

    VERSION = "V1"

    def __init__(self) -> None:
        self.name = "KAIRO"
        self.version = self.VERSION
        self.started_at = datetime.now()

        components = load_components()
        self.config = KairoConfig.from_environment()
        self.security = components["security"]()

        self._api_token = os.environ.get("KAIRO_API_TOKEN")
        self._api_identity = os.environ.get(
            "KAIRO_API_IDENTITY",
            "api-user",
        )
        api_permissions = tuple(
            permission.strip()
            for permission in os.environ.get(
                "KAIRO_API_PERMISSIONS",
                "",
            ).split(",")
            if permission.strip()
        )
        if self._api_token and api_permissions:
            self.security.provision_api_identity(
                self._api_identity,
                api_permissions,
            )

        self.runtime = components["runtime"](security=self.security)
        self.core = KairoCore(
            runtime=self.runtime,
            security=self.security,
        )
        self.agents: Any = self.core.orchestrator.agents
        self.engineering_agent = EngineeringAgent(
            security=self.security,
            repository_root=Path(__file__).resolve().parents[1],
            proposal_backend=self.core.orchestrator.reasoner.ai,
            runtime=self.runtime,
        )

        for agent in (
            CodingAgent(),
            DataAgent(),
            self.engineering_agent,
            ResearchAgent(),
        ):
            if getattr(agent, "name", None) == "engineering":
                AgentAuthority = import_module(
                    "02_AGENTS.authority"
                ).AgentAuthority
                Permission = import_module(
                    "02_AGENTS.authority"
                ).Permission
                self.agents.register(
                    agent,
                    AgentAuthority(
                        agent_name="engineering",
                        permissions=frozenset({
                            Permission.EXECUTE,
                            Permission.ENGINEERING_INSPECT,
                            Permission.ENGINEERING_PLAN,
                            Permission.ENGINEERING_MODIFY,
                            Permission.ENGINEERING_MODIFY_TESTS,
                            Permission.ENGINEERING_TEST,
                            Permission.ENGINEERING_CHECKPOINT,
                            Permission.ENGINEERING_ROLLBACK,
                            Permission.FILESYSTEM_WRITE,
                            Permission.PROCESS_EXECUTE,
                            Permission.MODEL_EXTERNAL,
                            Permission.CREATE_TASK,
                        }),
                    ),
                )
                continue
            self.agents.register(agent)

        database_root = (
            self.config.resolved_data_root()
            / "Database"
        )
        self.database = components["database"](
            database_root / "kairo_database.sqlite3"
        )
        self.knowledge = components["knowledge"](self.database)
        self.vector = components["vector"](self.database)
        memory_path = database_root / "kairo_memory.sqlite3"
        self.memory = components["memory"](memory_path)

        self.data = components["data_manager"](
            database=self.database,
            knowledge=self.knowledge,
            vector=self.vector,
            memory=self.memory,
        )

        tools_module = __import__("04_TOOLS.manager", fromlist=["ToolManager"])
        self.tools = tools_module.ToolManager(
            security=self.security,
        )
        EngineeringTool = import_module(
            "04_TOOLS.Engineering.tool"
        ).EngineeringTool
        for tool in (
            BrowserTool(),
            ComputerUseTool(),
            APITool(),
            MCPTool(),
            AutomationTool(),
            EngineeringTool(
                self.agents,
                self.engineering_agent,
            ),
        ):
            self.tools.register(tool)

    def health(self) -> dict[str, Any]:
        components: dict[str, dict[str, Any]] = {
            "core": self.core.health(),
            "model": self.core.orchestrator.reasoner.ai.status(),
            "runtime": self.runtime.health(),
            "agents": self.agents.health(),
            "engineering": self.engineering_health(),
            "data": self.data.health(),
            "tools": self.tools.health(),
            "security": self.security.health(),
        }
        statuses: list[str] = []
        for component in components.values():
            component_status = component.get(
                "status",
                component.get("core", "UNKNOWN"),
            )
            statuses.append(str(component_status))
        if "EMERGENCY_STOP" in statuses:
            status = "EMERGENCY_STOP"
        elif any(value in {"FAILED", "OFFLINE"} for value in statuses):
            status = "DEGRADED"
        elif any(value not in {"ONLINE", "HEALTHY"} for value in statuses):
            status = "DEGRADED"
        else:
            status = "ONLINE"
        return {
            "system": self.name,
            "version": self.version,
            "status": status,
            "started_at": self.started_at.isoformat(),
            "components": components,
        }

    def status(self) -> dict[str, Any]:
        return self.health()

    def respond(self, message: str, context: Any | None = None) -> str:
        return self.core.respond(message, context)

    def events(self, limit: int = 50) -> list[dict[str, Any]]:
        return self.core.events(limit)

    def component(self, name: str) -> Any:
        return getattr(self, name, None)

    def close(self) -> None:
        """Close persistent data resources owned by this system."""
        self.database.close()
        self.memory.close()

    def create_task(
        self,
        name: str,
        context: Any | None = None,
    ) -> dict[str, Any]:
        return self.runtime.create_task(name, context)

    def execute_agent(
        self,
        name: str,
        task: str,
        context: Any | None = None,
    ) -> Any:
        return self.agents.execute(name, task, context=context)

    def engineering_health(self) -> dict[str, Any]:
        if not hasattr(self.engineering_agent, "health"):
            return {"status": "UNAVAILABLE"}
        return self.engineering_agent.health()

    def remember(
        self,
        content: str,
        context: Any | None = None,
        *,
        scope: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Any:
        if context is None:
            effective_scope = scope or "default"
            operation_context = self._authorize_data_operation(
                None,
                "data.write",
                "memory.write",
                effective_scope,
            )
        else:
            effective_scope = self._scoped_memory_resource(
                context,
                scope or context.caller_identity,
                "memory.write",
            )
            operation_context = self._authorize_data_operation(
                context,
                "data.write",
                "memory.write",
                effective_scope,
            )
        record = self.memory.remember(
            content,
            scope=effective_scope,
            metadata=metadata,
        )
        self.security.audit_execution(operation_context, "COMPLETED")
        return record

    def recall(
        self,
        query: str,
        context: Any | None = None,
        *,
        scope: str | None = None,
        limit: int = 10,
    ) -> list[Any]:
        effective_scope = (
            context.caller_identity
            if scope is None and context is not None
            else scope
        )
        if context is not None:
            effective_scope = self._scoped_memory_resource(
                context,
                effective_scope or context.caller_identity,
                "memory.read",
            )
        operation_context = self._authorize_data_operation(
            context,
            "data.read",
            "memory.read",
            effective_scope or "all",
        )
        records = self.memory.recall(
            query,
            scope=effective_scope,
            limit=limit,
        )
        self.security.audit_execution(operation_context, "COMPLETED")
        return records

    def _scoped_memory_resource(
        self,
        context: Any,
        scope: str,
        operation: str,
    ) -> str:
        identity = self.security.identity.get(context.caller_identity)
        is_admin = (
            identity is not None
            and self.security.authority.get(
                context.caller_identity
            ).value >= 30
        )
        if scope != context.caller_identity and not is_admin:
            denied_context = context.derive(
                permission=(
                    "data.read"
                    if operation == "memory.read"
                    else "data.write"
                ),
                operation=operation,
                resource=scope,
            )
            self.security.audit_execution(
                denied_context,
                "DENY",
                "MEMORY_SCOPE_MISMATCH",
            )
            raise PermissionError(
                "Memory scope is not available to this identity."
            )
        return scope

    def _authorize_data_operation(
        self,
        context: Any | None,
        permission: str,
        operation: str,
        resource: str,
    ) -> Any:
        if context is None:
            self.security.audit.record(
                "AUTHORIZATION",
                None,
                operation,
                "DENY",
                {
                    "permission": permission,
                    "resource": resource,
                    "reason": "MISSING_CONTEXT",
                },
            )
            raise PermissionError(
                "Memory access requires an authorization context."
            )
        operation_context = context.derive(
            permission=permission,
            operation=operation,
            resource=resource,
        )
        decision = self.security.authorize_context(
            operation_context,
            permission,
        )
        if not decision.allowed:
            self.security.audit_execution(
                operation_context,
                decision.decision,
                decision.reason,
            )
            raise PermissionError(
                f"Memory access denied: {decision.reason}"
            )
        return operation_context

    def execution_context(
        self,
        identity_id: str,
        permission: str,
        operation: str,
        resource: str,
        *,
        origin: str = "internal",
        correlation_id: str | None = None,
        agent_identity: str | None = None,
        approval_id: str | None = None,
    ) -> Any:
        return self.security.context(
            identity_id,
            permission,
            operation,
            resource,
            agent_identity=agent_identity,
            origin=origin,
            correlation_id=correlation_id,
            approval_id=approval_id,
        )

    def authenticate_api_token(
        self,
        token: str | None,
        permission: str,
        operation: str,
        resource: str,
        correlation_id: str,
    ) -> Any | None:
        if not self._api_token or not token:
            return None
        if not hmac.compare_digest(self._api_token, token):
            return None
        return self.execution_context(
            self._api_identity,
            permission,
            operation,
            resource,
            origin="api",
            correlation_id=correlation_id,
        )

    def emergency_stop(self, context: Any | None = None) -> None:
        self.runtime.emergency_stop(context)
        self.agents.emergency_stop()
        self.security.set_emergency_stopped(True)

    def emergency_reset(self, context: Any | None = None) -> None:
        self.runtime.emergency_reset(context)
        self.agents.emergency_reset()
        self.security.set_emergency_stopped(False)

    def live_test(self, context: Any | None = None) -> dict[str, Any]:
        """Run a bounded end-to-end KAIRO system verification."""
        results: dict[str, Any] = {}

        results["startup"] = self.health()

        results["agents_before"] = self.agents.health()

        task = self.create_task(
            "KAIRO live system verification",
            context,
        )
        results["task"] = task

        coding = self.execute_agent(
            "coding",
            "Verify that KAIRO coding execution is connected to runtime.",
            context,
        )
        results["coding"] = (
            coding.__dict__
            if hasattr(coding, "__dict__")
            else coding
        )

        research = self.execute_agent(
            "research",
            "Verify that KAIRO research execution is connected to runtime.",
            context,
        )
        results["research"] = (
            research.__dict__
            if hasattr(research, "__dict__")
            else research
        )

        data = self.execute_agent(
            "data",
            "Verify that KAIRO data execution is connected to runtime.",
            context,
        )
        results["data"] = (
            data.__dict__
            if hasattr(data, "__dict__")
            else data
        )

        results["orchestrator"] = {
            "status": self.respond("status", context),
            "coding": self.respond(
                "code verify live KAIRO coding path",
                context,
            ),
            "research": self.respond(
                "research verify live KAIRO research path",
                context,
            ),
            "data": self.respond(
                "data verify live KAIRO data path",
                context,
            ),
        }

        results["agents_after"] = self.agents.health()
        results["runtime_after"] = self.runtime.health()
        results["security_after"] = self.security.health()
        results["events"] = self.events(100)

        results["final_status"] = self.health()

        return results

    def execute_tool(
        self,
        tool: str,
        action: str,
        arguments: dict[str, Any] | None = None,
        context: Any | None = None,
    ) -> Any:
        return self.tools.execute(
            tool,
            action,
            arguments,
            context=context,
        )