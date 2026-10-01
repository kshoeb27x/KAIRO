from src.kairo_system import KairoSystem
from importlib import import_module


AuthorityLevel = import_module(
    "06_SECURITY.Authority.authority"
).AuthorityLevel


def authorized_context(system: KairoSystem, *permissions: str):
    system.security.identity.create("test-user", "Test User")
    system.security.authority.assign("test-user", AuthorityLevel.USER)
    for permission in permissions:
        system.security.permissions.grant("test-user", permission)
    return system.security.context(
        "test-user",
        permissions[0],
        "test",
        "test",
    )


def test_system_shares_runtime_with_core() -> None:
    system = KairoSystem()

    assert system.core.runtime is system.runtime


def test_system_integrates_tools() -> None:
    system = KairoSystem()

    assert system.tools.list_tools() == [
        "api",
        "automation",
        "browser",
        "computer_use",
        "engineering",
        "mcp",
    ]
    assert system.health()["components"]["tools"]["status"] == "ONLINE"


def test_system_reports_unconfigured_model_as_offline() -> None:
    system = KairoSystem()

    health = system.health()

    assert health["components"]["model"]["status"] == "OFFLINE"
    assert health["status"] == "DEGRADED"


def test_system_executes_tool() -> None:
    system = KairoSystem()
    context = authorized_context(system, "network.read")

    result = system.execute_tool(
        "browser",
        "echo",
        {"message": "hello"},
        context,
    )

    assert result.status == "COMPLETED"
    assert result.result == {"message": "hello"}


def test_system_registers_and_executes_agents() -> None:
    system = KairoSystem()
    context = authorized_context(
        system,
        "agent.execute",
        "runtime.execute",
    )

    assert system.agents.list_agents() == [
        "coding",
        "data",
        "engineering",
        "research",
    ]

    result = system.execute_agent(
        "research",
        "find relevant facts",
        context,
    )

    assert result.status == "UNAVAILABLE"
    assert result.agent == "research"
    assert system.agents.health()["status"] == "DEGRADED"


def test_emergency_stop_is_reflected_in_system_health() -> None:
    system = KairoSystem()
    context = authorized_context(
        system,
        "runtime.emergency_stop",
    )

    system.emergency_stop(context)

    health = system.health()
    assert health["status"] == "EMERGENCY_STOP"
    assert health["components"]["runtime"]["status"] == "EMERGENCY_STOP"
    assert health["components"]["agents"]["status"] == "EMERGENCY_STOP"
    assert health["components"]["security"]["status"] == "EMERGENCY_STOP"
