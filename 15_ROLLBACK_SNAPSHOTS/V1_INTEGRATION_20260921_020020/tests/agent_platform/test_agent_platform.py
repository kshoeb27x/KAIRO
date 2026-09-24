from __future__ import annotations

import sys
from pathlib import Path
from importlib import import_module


PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(PROJECT_ROOT),
    )


agent_module = import_module(
    "02_AGENTS.agent"
)

execution_module = import_module(
    "02_AGENTS.execution"
)

manager_module = import_module(
    "02_AGENTS.manager"
)


AgentResult = (
    agent_module.AgentResult
)

AgentRequest = (
    execution_module.AgentRequest
)

AgentExecutor = (
    execution_module.AgentExecutor
)

AgentManager = (
    manager_module.AgentManager
)


class DemoAgent:

    name = "demo"

    def execute(
        self,
        task: str,
    ) -> AgentResult:

        return AgentResult(
            agent=self.name,
            task=task,
            status="COMPLETED",
            result={
                "message": "demo executed"
            },
        )


def test_agent_result_contract():

    result = AgentResult(
        agent="demo",
        task="hello",
        status="COMPLETED",
        result={
            "ok": True
        },
    )

    assert result.agent == "demo"
    assert result.task == "hello"
    assert result.status == "COMPLETED"


def test_executor_success():

    executor = AgentExecutor()

    result = executor.execute(
        DemoAgent(),
        AgentRequest(
            agent="demo",
            task="test",
        ),
    )

    assert result.status == "COMPLETED"
    assert result.agent == "demo"
    assert result.task == "test"


def test_executor_failure():

    class BrokenAgent:

        name = "broken"

        def execute(
            self,
            task: str,
        ):

            raise RuntimeError(
                "boom"
            )

    executor = AgentExecutor()

    result = executor.execute(
        BrokenAgent(),
        AgentRequest(
            agent="broken",
            task="test",
        ),
    )

    assert result.status == "FAILED"
    assert "boom" in result.result


def test_manager_registration():

    manager = AgentManager()

    manager.register(
        DemoAgent()
    )

    assert (
        manager.get("demo")
        is not None
    )

    assert manager.list_agents() == [
        "demo"
    ]


def test_manager_execution():

    manager = AgentManager()

    manager.register(
        DemoAgent()
    )

    result = manager.execute(
        "demo",
        "live test",
    )

    assert result.status == "COMPLETED"
    assert result.agent == "demo"


def test_manager_health():

    manager = AgentManager()

    manager.register(
        DemoAgent()
    )

    health = manager.health()

    assert health["status"] == "ONLINE"
    assert health["count"] == 1
    assert health["agents"] == [
        "demo"
    ]
