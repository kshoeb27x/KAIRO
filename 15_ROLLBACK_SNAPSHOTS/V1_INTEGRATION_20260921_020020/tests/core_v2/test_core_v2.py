from src.core.kairo_core import KairoCore


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
    core = KairoCore()

    result = core.create_task("core integration test")

    assert result["name"] == "core integration test"


def test_response():
    core = KairoCore()

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

    core = KairoCore()

    core.register_agent(DemoAgent())

    assert core.list_agents() == ["demo"]

    result = core.execute_agent(
        "demo",
        "test task",
    )

    assert result["status"] == "COMPLETED"

    assert core.unregister_agent("demo") is True
    assert core.list_agents() == []
