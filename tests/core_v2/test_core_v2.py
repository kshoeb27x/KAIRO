from src.core.kairo_core import KairoCore
from importlib import import_module
from types import SimpleNamespace


SecurityManager = import_module(
    "06_SECURITY.security_manager"
).SecurityManager
AuthorityLevel = import_module(
    "06_SECURITY.Authority.authority"
).AuthorityLevel
RuntimeManager = import_module(
    "07_RUNTIME.runtime_manager"
).RuntimeManager


def create_security(*permissions: str):
    security = SecurityManager()
    security.identity.create("core-user", "Core User")
    security.authority.assign("core-user", AuthorityLevel.USER)
    for permission in permissions:
        security.permissions.grant("core-user", permission)
    return security


def test_core_starts():
    core = KairoCore()

    assert core.name == "KAIRO"
    assert core.version == "V2"


def test_health():
    core = KairoCore()

    result = core.health()

    assert result["system"] == "KAIRO"
    assert result["version"] == "V2"
    assert result["core"] == "ONLINE"


def test_task_creation():
    security = create_security("runtime.task.create")
    core = KairoCore(
        runtime=RuntimeManager(security),
        security=security,
    )

    result = core.create_task(
        "core integration test",
        security.context(
            "core-user",
            "runtime.task.create",
            "task.create",
            "core integration test",
        ),
    )

    assert result["name"] == "core integration test"


def test_orchestrator_preserves_execution_context_for_task_creation():
    security = create_security("runtime.task.create")
    security.permissions.grant("core-user", "runtime.task.read")
    core = KairoCore(
        runtime=RuntimeManager(security),
        security=security,
    )
    context = security.context(
        "core-user",
        "runtime.task.create",
        "api.chat",
        "orchestrator",
        origin="test",
        correlation_id="core-task-context",
    )

    response = core.respond("create task propagated context", context)

    read_context = security.context(
        "core-user",
        "runtime.task.read",
        "task.list",
        "tasks",
    )
    task = core.runtime.tasks.list_tasks(read_context)[0]
    assert response.startswith("Task created:")
    assert task["identity"] == "core-user"
    assert task["correlation_id"] == "core-task-context"


def test_reasoner_propagates_execution_context_to_model_provider():
    reasoner_type = import_module("Reasoning.reasoner").KairoReasoner
    captured = {}

    class Provider:
        def generate(self, prompt, context):
            captured["prompt"] = prompt
            captured["context"] = context
            return SimpleNamespace(content="provider response")

    execution_context = object()
    reasoner = reasoner_type(ai=Provider())

    result = reasoner.analyze(
        "summarize this",
        execution_context=execution_context,
    )

    assert result.reasoning == "provider response"
    assert captured == {
        "prompt": "summarize this",
        "context": execution_context,
    }


def test_orchestrator_model_call_is_authorized():
    security = create_security("model.external")
    core = KairoCore(
        runtime=RuntimeManager(security),
        security=security,
    )
    generated = []

    class Provider:
        def generate(self, prompt):
            generated.append(prompt)
            return SimpleNamespace(content="authorized response")

    core.orchestrator.reasoner.ai.provider = Provider()
    context = security.context(
        "core-user",
        "api.chat",
        "api.chat",
        "orchestrator",
    )
    model_context = context.derive(
        permission="model.external",
        operation="model.generate",
        resource="configured-provider",
        requested_capability="model.external",
    )
    security.identity.create("model-admin", "Model Admin")
    security.authority.assign("model-admin", AuthorityLevel.ADMIN)
    security.permissions.grant("model-admin", "security.approve")
    context = context.derive(
        approval_id=security.approve(model_context, "model-admin"),
    )

    response = core.respond("explain the runtime", context)

    assert response == "authorized response"
    assert generated == ["explain the runtime"]
    assert any(
        entry["status"] == "ALLOW"
        and entry["action"] == "model.generate"
        for entry in security.audit.recent()
    )


def test_orchestrator_model_call_denies_without_permission():
    security = create_security()
    core = KairoCore(
        runtime=RuntimeManager(security),
        security=security,
    )
    generated = []

    class Provider:
        def generate(self, prompt):
            generated.append(prompt)
            return SimpleNamespace(content="must not execute")

    core.orchestrator.reasoner.ai.provider = Provider()
    context = security.context(
        "core-user",
        "api.chat",
        "api.chat",
        "orchestrator",
    )

    try:
        core.respond("explain the runtime", context)
    except PermissionError:
        pass
    else:
        raise AssertionError("Unauthorized model generation was allowed.")

    assert generated == []
    assert any(
        entry["status"] == "DENY"
        and entry["action"] == "model.generate"
        for entry in security.audit.recent()
    )


def test_unconfigured_model_provider_fails_explicitly():
    ai_type = import_module("AI.ai").KairoAI
    ai = ai_type()

    assert ai.status() == {
        "layer": "AI",
        "status": "OFFLINE",
        "provider": "unconfigured",
    }
    try:
        ai.generate("answer this")
    except RuntimeError as error:
        assert "No AI provider is configured" in str(error)
    else:
        raise AssertionError(
            "Unconfigured AI provider returned a fabricated response."
        )


def test_model_provider_denies_and_audits_missing_context():
    ai_type = import_module("AI.ai").KairoAI
    security = create_security("model.external")
    generated = []

    class Provider:
        def generate(self, prompt):
            generated.append(prompt)
            return SimpleNamespace(content="must not execute")

    ai = ai_type(provider=Provider(), security=security)
    try:
        ai.generate("explain the runtime")
    except PermissionError:
        pass
    else:
        raise AssertionError("Model generation without context was allowed.")

    assert generated == []
    assert any(
        entry["event"] == "AUTHORIZATION"
        and entry["action"] == "model.generate"
        and entry["status"] == "DENY"
        for entry in security.audit.recent()
    )


def test_response():
    security = create_security(
        "agent.execute",
        "runtime.execute",
    )
    core = KairoCore(
        runtime=RuntimeManager(security),
        security=security,
    )

    result = core.respond("hello")

    assert isinstance(result, str)
    assert result


def test_agent_registry():
    class DemoAgent:
        name = "demo"

        def execute(self, task):
            return {
                "agent": self.name,
                "task": task,
                "status": "COMPLETED",
            }

    security = create_security(
        "agent.execute",
        "runtime.execute",
    )
    core = KairoCore(
        runtime=RuntimeManager(security),
        security=security,
    )

    core.register_agent(DemoAgent())

    assert core.list_agents() == ["demo"]

    result = core.execute_agent(
        "demo",
        "test task",
        security.context(
            "core-user",
            "agent.execute",
            "agent.execute",
            "demo",
        ),
    )

    assert result["status"] == "COMPLETED"

    assert core.unregister_agent("demo") is True
    assert core.list_agents() == []


def test_explicit_engineering_objective_routes_to_engineering_agent():
    security = create_security(
        "agent.execute",
        "runtime.execute",
    )
    core = KairoCore(
        runtime=RuntimeManager(security),
        security=security,
    )
    calls = []

    class EngineeringStub:
        name = "engineering"

        def execute(self, task, context=None):
            calls.append((task, context))
            return {
                "status": "BLOCKED_EXTERNAL",
                "result": "No approved proposal backend is configured.",
            }

    core.register_agent(EngineeringStub())
    context = security.context(
        "core-user",
        "api.chat",
        "api.chat",
        "orchestrator",
    )

    response = core.respond(
        "implement Engineering Agent",
        context,
    )

    assert len(calls) == 1
    assert calls[0][0] == "implement Engineering Agent"
    assert calls[0][1].caller_identity == "core-user"
    assert "BLOCKED_EXTERNAL" in response


def test_orchestrator_preserves_execution_context_for_agent_execution():
    security = create_security(
        "agent.execute",
        "runtime.execute",
    )
    core = KairoCore(
        runtime=RuntimeManager(security),
        security=security,
    )

    class ResearchAgent:
        name = "research"

        def execute(self, task):
            return f"researched: {task}"

    core.register_agent(ResearchAgent())
    context = security.context(
        "core-user",
        "agent.execute",
        "api.chat",
        "orchestrator",
        origin="test",
        correlation_id="core-agent-context",
    )

    response = core.respond("research source details", context)

    assert response == "researched: source details"
    assert security.audit.durable_recent()[-1]["details"]["correlation_id"] == (
        "core-agent-context"
    )
