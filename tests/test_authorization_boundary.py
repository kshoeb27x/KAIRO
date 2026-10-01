from __future__ import annotations

import importlib
import json
from io import BytesIO

import pytest


ExecutionContext = importlib.import_module(
    "06_SECURITY.execution_context"
).ExecutionContext
SecurityManager = importlib.import_module(
    "06_SECURITY.security_manager"
).SecurityManager
AuthorityLevel = importlib.import_module(
    "06_SECURITY.Authority.authority"
).AuthorityLevel
AgentAuthority = importlib.import_module(
    "02_AGENTS.authority"
).AgentAuthority
AgentPermission = importlib.import_module(
    "02_AGENTS.authority"
).Permission
AgentManager = importlib.import_module(
    "02_AGENTS.Manager.agent_manager"
).AgentManager
RuntimeManager = importlib.import_module(
    "07_RUNTIME.runtime_manager"
).RuntimeManager
ToolDefinition = importlib.import_module(
    "04_TOOLS.tool"
).ToolDefinition
ToolManager = importlib.import_module(
    "04_TOOLS.manager"
).ToolManager
KairoSystem = importlib.import_module(
    "src.kairo_system"
).KairoSystem


def create_security(*permissions: str) -> SecurityManager:
    security = SecurityManager()
    security.identity.create("user-1", "Test User")
    security.authority.assign("user-1", AuthorityLevel.USER)
    for permission in permissions:
        security.permissions.grant("user-1", permission)
    return security


def make_context(
    security: SecurityManager,
    permission: str,
    *,
    operation: str = "test",
    resource: str = "test-resource",
    agent_identity: str | None = None,
) -> ExecutionContext:
    return security.context(
        "user-1",
        permission,
        operation,
        resource,
        agent_identity=agent_identity,
        correlation_id="request-test-1",
    )


def test_security_allows_granted_permission_and_audits_correlation() -> None:
    security = create_security("data.read")
    context = make_context(security, "data.read")

    decision = security.authorize(context)

    assert decision.decision == "ALLOW"
    assert security.audit.recent()[-1]["details"]["correlation_id"] == "request-test-1"


def test_security_audit_is_durable_and_excludes_request_payloads(
    tmp_path,
) -> None:
    audit_type = importlib.import_module(
        "06_SECURITY.Audit.audit"
    ).AuditLogger
    audit = audit_type(tmp_path / "audit.sqlite3")

    audit.record(
        "AUTHORIZATION",
        "user-1",
        "data.read",
        "ALLOW",
        {"correlation_id": "corr-1"},
    )

    durable = audit_type(tmp_path / "audit.sqlite3").durable_recent()
    assert durable[-1]["identity_id"] == "user-1"
    assert durable[-1]["details"] == {"correlation_id": "corr-1"}


def test_security_denies_missing_identity_and_unknown_permission() -> None:
    security = SecurityManager()
    unknown = security.context(
        "unregistered",
        "made.up.permission",
        "test",
        "resource",
    )

    decision = security.authorize(unknown)

    assert decision.decision == "DENY"
    assert decision.reason == "UNKNOWN_PERMISSION"
    assert security.audit.recent()[-1]["status"] == "DENY"


def test_security_denies_valid_permission_for_invalid_identity() -> None:
    security = SecurityManager()
    context = security.context(
        "missing-user",
        "data.read",
        "data.read",
        "knowledge",
    )

    decision = security.authorize(context)

    assert decision.decision == "DENY"
    assert decision.reason == "UNKNOWN_OR_INACTIVE_IDENTITY"


def test_tool_permission_metadata_is_enforced_before_handler() -> None:
    class CountingTool:
        definition = ToolDefinition(
            name="counter",
            description="test",
            category="test",
            permissions=["network.read"],
        )

        def __init__(self) -> None:
            self.called = False

        def execute(self, action: str, arguments: dict) -> dict:
            self.called = True
            return {"ok": True}

    security = create_security()
    manager = ToolManager(security)
    tool = CountingTool()
    manager.register(tool)
    context = make_context(security, "tool.invoke")

    result = manager.execute("counter", "run", context=context)

    assert result.status == "DENIED"
    assert tool.called is False


def test_authorized_tool_executes_and_is_audited() -> None:
    class EchoTool:
        definition = ToolDefinition(
            name="echo",
            description="test",
            category="test",
            permissions=["data.read"],
        )

        def execute(self, action: str, arguments: dict) -> dict:
            return {"message": arguments["message"]}

    security = create_security("data.read")
    manager = ToolManager(security)
    manager.register(EchoTool())
    context = make_context(security, "data.read", operation="tool.echo")

    result = manager.execute(
        "echo",
        "run",
        {"message": "ok"},
        context=context,
    )

    assert result.status == "COMPLETED"
    assert result.result == {"message": "ok"}
    assert security.audit.recent()[-1]["event"] == "EXECUTION"


def test_computer_use_tool_requires_computer_capability() -> None:
    security = create_security("tool.invoke")
    manager = ToolManager(security)
    computer_tool = importlib.import_module(
        "04_TOOLS.Computer_Use.tool"
    ).ComputerUseTool
    manager.register(computer_tool())

    result = manager.execute(
        "computer_use",
        "echo",
        {"message": "must not run"},
        context=make_context(
            security,
            "tool.invoke",
            operation="computer.echo",
        ),
    )

    assert result.status == "DENIED"
    assert result.error == "PERMISSION_NOT_GRANTED"


def test_agent_requires_caller_and_agent_authority() -> None:
    security = create_security("agent.execute", "runtime.execute")
    runtime = RuntimeManager(security)
    manager = AgentManager(runtime, security)

    class DemoAgent:
        name = "demo"

        def execute(self, task: str) -> str:
            return task

    manager.register(DemoAgent())
    context = make_context(security, "agent.execute")

    result = manager.execute("demo", "run", context=context)

    assert result.status == "COMPLETED"
    assert result.result == "run"
    assert result.request_id


def test_unauthorized_agent_execution_fails_closed() -> None:
    security = create_security("runtime.execute")
    runtime = RuntimeManager(security)
    manager = AgentManager(runtime, security)

    class DemoAgent:
        name = "demo"
        called = False

        def execute(self, task: str) -> str:
            self.called = True
            return task

    agent = DemoAgent()
    manager.register(agent)

    with pytest.raises(PermissionError):
        manager.execute(
            "demo",
            "blocked",
            context=make_context(security, "agent.execute"),
        )

    assert agent.called is False


def test_agent_local_authority_cannot_exceed_caller_or_agent_grant() -> None:
    security = create_security("agent.execute", "runtime.execute")
    runtime = RuntimeManager(security)
    manager = AgentManager(runtime, security)

    class RestrictedAgent:
        name = "restricted"
        called = False

        def execute(self, task: str) -> str:
            self.called = True
            return task

    agent = RestrictedAgent()
    manager.register(
        agent,
        AgentAuthority(
            agent_name="restricted",
            permissions=frozenset(),
        ),
    )

    with pytest.raises(PermissionError):
        manager.execute(
            "restricted",
            "must not run",
            context=make_context(security, "agent.execute"),
        )

    assert agent.called is False


def test_runtime_requires_context_and_propagates_identity() -> None:
    security = create_security("runtime.task.create")
    runtime = RuntimeManager(security)

    with pytest.raises(PermissionError):
        runtime.create_task("missing context")
    with pytest.raises(PermissionError):
        runtime.tasks.create("direct missing context")

    context = make_context(
        security,
        "runtime.task.create",
        operation="task.create",
        resource="task",
    )
    task = runtime.create_task("authorized", context)

    assert task["identity"] == "user-1"
    assert task["correlation_id"] == "request-test-1"


def test_task_reads_require_permission_and_enforce_identity_scope() -> None:
    security = create_security(
        "runtime.task.create",
        "runtime.task.read",
    )
    runtime = RuntimeManager(security)
    created = runtime.create_task(
        "private task",
        make_context(
            security,
            "runtime.task.create",
            operation="task.create",
            resource="private task",
        ),
    )

    with pytest.raises(PermissionError):
        runtime.tasks.list_tasks()
    with pytest.raises(PermissionError):
        runtime.tasks.get(created["id"])

    security.identity.create("other-user", "Other User")
    security.authority.assign("other-user", AuthorityLevel.USER)
    security.permissions.grant("other-user", "runtime.task.read")
    security.permissions.grant("other-user", "runtime.execute")
    reader_context = security.context(
        "other-user",
        "runtime.task.read",
        "task.list",
        "tasks",
    )

    assert runtime.tasks.list_tasks(reader_context) == []
    foreign_task_context = reader_context.derive(
        operation="task.read",
        resource=str(created["id"]),
    )
    with pytest.raises(PermissionError):
        runtime.tasks.get(created["id"], foreign_task_context)
    with pytest.raises(PermissionError):
        runtime.tasks.complete(
            created["id"],
            {"tampered": True},
            reader_context.derive(
                permission="runtime.execute",
                operation="task.complete",
                resource=str(created["id"]),
            ),
        )
    assert runtime.tasks.get(
        created["id"],
        make_context(
            security,
            "runtime.task.read",
            operation="task.read",
            resource=str(created["id"]),
        ),
    )["status"] == "PENDING"


def test_runtime_executor_internals_require_authorized_context() -> None:
    security = create_security("runtime.execute")
    runtime = RuntimeManager(security)
    called = False

    def operation() -> str:
        nonlocal called
        called = True
        return "done"

    with pytest.raises(PermissionError):
        runtime.executor.execute("direct", operation)
    assert called is False

    result = runtime.executor.execute(
        "direct",
        operation,
        context=make_context(
            security,
            "runtime.execute",
            operation="runtime.execute",
            resource="direct",
        ),
    )

    assert result.status == "COMPLETED"
    assert called is True


def test_runtime_executor_propagates_context_to_callable() -> None:
    security = create_security("runtime.execute")
    runtime = RuntimeManager(security)
    received: list[str] = []

    result = runtime.execute(
        "context-aware",
        lambda context: received.append(context.correlation_id),
        context=make_context(
            security,
            "runtime.execute",
            operation="runtime.execute",
            resource="context-aware",
        ),
    )

    assert result.status == "COMPLETED"
    assert received == ["request-test-1"]


def test_workflow_authorizes_each_step_under_same_context() -> None:
    security = create_security("runtime.workflow.execute")
    runtime = RuntimeManager(security)
    context = make_context(
        security,
        "runtime.workflow.execute",
        operation="workflow",
        resource="wf",
    )
    called = False
    workflow = runtime.workflow("wf", context)

    def step() -> str:
        nonlocal called
        called = True
        return "done"

    workflow.add_step("requires-runtime-execute", step)
    result = workflow.run()

    assert result.status == "FAILED"
    assert called is False
    assert security.audit.recent()[-1]["event"] == "EXECUTION"


def test_workflow_propagates_context_to_each_step() -> None:
    security = create_security(
        "runtime.workflow.execute",
        "runtime.execute",
    )
    runtime = RuntimeManager(security)
    context = make_context(
        security,
        "runtime.workflow.execute",
        operation="workflow",
        resource="wf",
    )
    received: list[str] = []
    workflow = runtime.workflow("wf", context)
    workflow.add_step(
        "one",
        lambda context: received.append(context.correlation_id),
    )

    result = workflow.run()

    assert result.status == "COMPLETED"
    assert received == ["request-test-1"]


def test_caller_approval_boolean_does_not_authorize_sandbox() -> None:
    security = create_security("filesystem.write")
    context = make_context(
        security,
        "filesystem.write",
        operation="sandbox.write",
        resource="filesystem_write",
    )
    called = False

    def operation() -> str:
        nonlocal called
        called = True
        return "done"

    request_type = importlib.import_module(
        "06_SECURITY.Sandbox.provider"
    ).SandboxRequest
    request = request_type(
        operation="write",
        capability="filesystem_write",
        approved=True,
    )

    with pytest.raises(PermissionError):
        security.sandbox_provider.execute(request, operation, context)

    assert called is False
    assert any(
        entry["status"] == "REQUIRES_APPROVAL"
        for entry in security.audit.recent()
    )


def test_emergency_stop_blocks_runtime_execution() -> None:
    security = create_security(
        "runtime.emergency_stop",
        "runtime.execute",
    )
    runtime = RuntimeManager(security)
    stop_context = make_context(
        security,
        "runtime.emergency_stop",
        operation="runtime.emergency_stop",
        resource="runtime",
    )
    runtime.emergency_stop(stop_context)
    called = False

    def operation() -> None:
        nonlocal called
        called = True

    with pytest.raises(PermissionError):
        runtime.execute(
            "blocked",
            operation,
            context=make_context(security, "runtime.execute"),
        )

    assert called is False


def test_api_task_creation_requires_authenticated_authorized_caller(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KAIRO_API_TOKEN", "local-test-token")
    monkeypatch.setenv("KAIRO_API_IDENTITY", "api-test-user")
    monkeypatch.setenv(
        "KAIRO_API_PERMISSIONS",
        "api.tasks.create,runtime.task.create,runtime.task.read",
    )
    system = KairoSystem()
    api_module = importlib.import_module("src.api.server")
    monkeypatch.setattr(api_module, "kairo", system)
    responses: list[tuple[dict, int]] = []

    def post(headers: dict[str, str]) -> tuple[dict, int]:
        body = b'{"name":"api task"}'
        handler = api_module.KairoHandler.__new__(
            api_module.KairoHandler
        )
        handler.path = "/api/tasks"
        handler.headers = {
            **headers,
            "Content-Length": str(len(body)),
        }
        handler.rfile = BytesIO(body)
        handler.send_json = lambda data, status=200: responses.append(  # type: ignore[method-assign]
            (data, status)
        )
        handler.do_POST()
        return responses[-1]

    denied, denied_status = post({})
    assert denied_status == 401
    assert denied["error"] == "Authentication required."
    read_context = system.execution_context(
        "api-test-user",
        "runtime.task.read",
        "task.list",
        "tasks",
    )
    assert system.runtime.tasks.list_tasks(read_context) == []

    accepted, accepted_status = post(
        {"Authorization": "Bearer local-test-token"}
    )
    assert accepted_status == 201
    assert accepted["task"]["identity"] == "api-test-user"


def test_api_agent_and_tool_routes_require_api_and_operation_permissions(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("KAIRO_DATA_ROOT", str(tmp_path))
    monkeypatch.setenv("KAIRO_API_TOKEN", "local-test-token")
    monkeypatch.setenv("KAIRO_API_IDENTITY", "api-test-user")
    monkeypatch.setenv(
        "KAIRO_API_PERMISSIONS",
        "api.agents.execute,agent.execute,runtime.execute,"
        "api.tools.execute,network.read",
    )
    system = KairoSystem()
    api_module = importlib.import_module("src.api.server")
    monkeypatch.setattr(api_module, "kairo", system)

    def post(path: str, payload: dict) -> tuple[dict, int]:
        body = json.dumps(payload).encode()
        handler = api_module.KairoHandler.__new__(
            api_module.KairoHandler
        )
        handler.path = path
        handler.headers = {
            "Authorization": "Bearer local-test-token",
            "Content-Length": str(len(body)),
        }
        handler.rfile = BytesIO(body)
        responses: list[tuple[dict, int]] = []
        handler.send_json = lambda data, status=200: responses.append(  # type: ignore[method-assign]
            (data, status)
        )
        handler.do_POST()
        return responses[-1]

    try:
        agent_response, agent_status = post(
            "/api/agents/research/execute",
            {"task": "verify a fact"},
        )
        assert agent_status == 503
        assert agent_response["result"]["status"] == "UNAVAILABLE"

        tool_response, tool_status = post(
            "/api/tools/browser/echo",
            {"arguments": {"message": "authorized"}},
        )
        assert tool_status == 200
        assert tool_response["result"]["result"] == {
            "message": "authorized",
        }

        denied_response, denied_status = post(
            "/api/tools/computer_use/echo",
            {"arguments": {"message": "not authorized"}},
        )
        assert denied_status == 403
        assert denied_response["error"] == "PERMISSION_NOT_GRANTED"
    finally:
        system.close()


def test_api_memory_routes_require_data_permissions_and_scope_to_identity(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("KAIRO_DATA_ROOT", str(tmp_path))
    monkeypatch.setenv("KAIRO_API_TOKEN", "local-test-token")
    monkeypatch.setenv("KAIRO_API_IDENTITY", "api-memory-user")
    monkeypatch.setenv(
        "KAIRO_API_PERMISSIONS",
        "api.memory.read,api.memory.write,data.read,data.write",
    )
    system = KairoSystem()
    api_module = importlib.import_module("src.api.server")
    monkeypatch.setattr(api_module, "kairo", system)

    def request(
        method: str,
        path: str,
        payload: dict | None = None,
    ) -> tuple[dict, int]:
        body = json.dumps(payload or {}).encode()
        handler = api_module.KairoHandler.__new__(
            api_module.KairoHandler
        )
        handler.path = path
        handler.headers = {
            "Authorization": "Bearer local-test-token",
            "Content-Length": str(len(body)),
        }
        handler.rfile = BytesIO(body)
        responses: list[tuple[dict, int]] = []
        handler.send_json = lambda data, status=200: responses.append(  # type: ignore[method-assign]
            (data, status)
        )
        if method == "POST":
            handler.do_POST()
        else:
            handler.do_GET()
        return responses[-1]

    try:
        created, create_status = request(
            "POST",
            "/api/memory",
            {"content": "KAIRO secure memory fact"},
        )
        assert create_status == 201
        assert created["memory"]["scope"] == "api-memory-user"

        recalled, recall_status = request(
            "GET",
            "/api/memory?q=secure%20memory",
        )
        assert recall_status == 200
        assert len(recalled["memories"]) == 1
        assert recalled["memories"][0]["scope"] == "api-memory-user"
    finally:
        system.close()


def test_api_emergency_stop_requires_permissions_and_stops_runtime(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("KAIRO_DATA_ROOT", str(tmp_path))
    monkeypatch.setenv("KAIRO_API_TOKEN", "local-test-token")
    monkeypatch.setenv("KAIRO_API_IDENTITY", "api-stop-user")
    monkeypatch.setenv(
        "KAIRO_API_PERMISSIONS",
        "api.runtime.control,runtime.emergency_stop",
    )
    system = KairoSystem()
    api_module = importlib.import_module("src.api.server")
    monkeypatch.setattr(api_module, "kairo", system)

    def post(headers: dict[str, str]) -> tuple[dict, int]:
        handler = api_module.KairoHandler.__new__(
            api_module.KairoHandler
        )
        handler.path = "/api/runtime/emergency-stop"
        handler.headers = {
            **headers,
            "Content-Length": "0",
        }
        handler.rfile = BytesIO(b"")
        responses: list[tuple[dict, int]] = []
        handler.send_json = lambda data, status=200: responses.append(  # type: ignore[method-assign]
            (data, status)
        )
        handler.do_POST()
        return responses[-1]

    try:
        denied, denied_status = post({})
        assert denied_status == 401
        assert denied["error"] == "Authentication required."
        assert system.runtime.health()["status"] == "ONLINE"

        stopped, stopped_status = post({
            "Authorization": "Bearer local-test-token",
        })
        assert stopped_status == 202
        assert stopped["status"] == "EMERGENCY_STOP"
        assert system.health()["status"] == "EMERGENCY_STOP"
    finally:
        system.close()


def test_system_memory_access_cannot_cross_identity_scopes(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KAIRO_DATA_ROOT", str(tmp_path))
    system = KairoSystem()
    system.security.identity.create("memory-owner", "Owner")
    system.security.authority.assign("memory-owner", AuthorityLevel.USER)
    system.security.permissions.grant("memory-owner", "data.read")
    system.security.permissions.grant("memory-owner", "data.write")
    system.security.identity.create("memory-reader", "Reader")
    system.security.authority.assign("memory-reader", AuthorityLevel.USER)
    system.security.permissions.grant("memory-reader", "data.read")
    system.memory.remember(
        "private owner content",
        scope="memory-owner",
    )
    reader_context = system.security.context(
        "memory-reader",
        "data.read",
        "memory.read",
        "memory-owner",
    )

    try:
        with pytest.raises(PermissionError):
            system.recall(
                "private",
                reader_context,
                scope="memory-owner",
            )
        assert system.security.audit.recent()[-1]["details"]["error"] == (
            "[REDACTED]"
        )
    finally:
        system.close()


def test_delegation_is_denied_without_source_delegation_capability() -> None:
    security = create_security(
        "agent.execute",
        "runtime.execute",
    )
    runtime = RuntimeManager(security)
    manager = AgentManager(runtime, security)

    class DemoAgent:
        def __init__(self, name: str) -> None:
            self.name = name

        def execute(self, task: str) -> str:
            return task

    manager.register(DemoAgent("source"))
    manager.register(DemoAgent("target"))
    source_context = make_context(
        security,
        "agent.execute",
        agent_identity="agent:source",
    )

    with pytest.raises(PermissionError):
        manager.delegate(
            "source",
            "target",
            "delegated",
            source_context,
        )


def test_delegation_succeeds_only_with_explicit_bounded_authority() -> None:
    security = create_security(
        "agent.execute",
        "agent.delegate",
        "runtime.execute",
    )
    runtime = RuntimeManager(security)
    manager = AgentManager(runtime, security)

    class DemoAgent:
        def __init__(self, name: str) -> None:
            self.name = name

        def execute(self, task: str) -> str:
            return f"{self.name}:{task}"

    manager.register(
        DemoAgent("source"),
        AgentAuthority(
            agent_name="source",
            permissions=frozenset({
                AgentPermission.EXECUTE,
                AgentPermission.DELEGATE,
            }),
        ),
    )
    manager.register(DemoAgent("target"))
    source_context = make_context(
        security,
        "agent.execute",
        agent_identity="agent:source",
    )

    result = manager.delegate(
        "source",
        "target",
        "bounded",
        source_context,
    )

    assert result.status == "COMPLETED"
    assert result.result == "target:bounded"
    assert any(
        entry["details"].get("delegated_by") == "source"
        for entry in security.audit.recent()
    )


def test_delegated_agent_cannot_use_permission_delegator_lacks() -> None:
    security = create_security(
        "agent.execute",
        "agent.delegate",
        "runtime.execute",
        "data.read",
    )
    runtime = RuntimeManager(security)
    manager = AgentManager(runtime, security)

    class SourceAgent:
        name = "source"

        def execute(self, task: str) -> str:
            return task

    class DataAgent:
        name = "data-agent"

        def execute(self, task: str, context=None) -> str:
            decision = security.authorize_context(
                context.derive(
                    permission="data.read",
                    operation="data.read",
                    resource="knowledge",
                )
            )
            if not decision.allowed:
                raise PermissionError(decision.reason)
            return "read"

    manager.register(
        SourceAgent(),
        AgentAuthority(
            agent_name="source",
            permissions=frozenset({
                AgentPermission.EXECUTE,
                AgentPermission.DELEGATE,
            }),
        ),
    )
    manager.register(
        DataAgent(),
        AgentAuthority(
            agent_name="data-agent",
            permissions=frozenset({
                AgentPermission.EXECUTE,
                AgentPermission.READ_DATA,
            }),
        ),
    )
    source_context = make_context(
        security,
        "agent.execute",
        agent_identity="agent:source",
    )

    result = manager.delegate(
        "source",
        "data-agent",
        "read data",
        source_context,
    )

    assert result.status == "FAILED"
    assert any(
        entry["details"].get("reason")
        == "DELEGATED_PERMISSION_EXCEEDS_DELEGATOR"
        for entry in security.audit.recent()
    )
