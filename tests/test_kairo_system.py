from src.kairo_system import KairoSystem


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
        "mcp",
    ]
    assert system.health()["components"]["tools"]["status"] == "ONLINE"


def test_system_executes_tool() -> None:
    system = KairoSystem()

    result = system.execute_tool(
        "browser",
        "echo",
        {"message": "hello"},
    )

    assert result.status == "COMPLETED"
    assert result.result == {"message": "hello"}


def test_system_registers_and_executes_agents() -> None:
    system = KairoSystem()

    assert system.agents.list_agents() == ["coding", "data", "research"]

    result = system.execute_agent("research", "find relevant facts")

    assert result.status == "COMPLETED"
    assert result.agent == "research"
