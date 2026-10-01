from __future__ import annotations

import sys
from pathlib import Path
from importlib import import_module

PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if str(PROJECT_ROOT / "02_AGENTS") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "02_AGENTS"))


AgentManager = import_module(
    "02_AGENTS.manager"
).AgentManager

AgentAuthority = import_module(
    "02_AGENTS.authority"
).AgentAuthority

Permission = import_module(
    "02_AGENTS.authority"
).Permission

AgentState = import_module(
    "02_AGENTS.authority"
).AgentState
SecurityManager = import_module(
    "06_SECURITY.security_manager"
).SecurityManager
AuthorityLevel = import_module(
    "06_SECURITY.Authority.authority"
).AuthorityLevel

CodingAgent = import_module(
    "02_AGENTS.Coding.coding_agent"
).CodingAgent

DataAgent = import_module(
    "02_AGENTS.Data.data_agent"
).DataAgent

ResearchAgent = import_module(
    "02_AGENTS.Research.research_agent"
).ResearchAgent


def build_manager() -> AgentManager:
    security = SecurityManager()
    security.identity.create("agent-test-user", "Agent Test User")
    security.authority.assign(
        "agent-test-user",
        AuthorityLevel.USER,
    )
    security.permissions.grant(
        "agent-test-user",
        "agent.execute",
    )
    security.permissions.grant(
        "agent-test-user",
        "runtime.execute",
    )
    manager = AgentManager(security=security)

    manager.register(
        CodingAgent(),
        AgentAuthority(
            agent_name="coding",
            permissions=frozenset({
                Permission.EXECUTE,
                Permission.READ_DATA,
            }),
        ),
    )

    manager.register(
        DataAgent(),
        AgentAuthority(
            agent_name="data",
            permissions=frozenset({
                Permission.EXECUTE,
                Permission.READ_DATA,
                Permission.WRITE_DATA,
            }),
        ),
    )

    manager.register(
        ResearchAgent(),
        AgentAuthority(
            agent_name="research",
            permissions=frozenset({
                Permission.EXECUTE,
                Permission.READ_DATA,
                Permission.NETWORK,
            }),
        ),
    )

    return manager


def execution_context(manager: AgentManager):
    return manager.security.context(
        "agent-test-user",
        "agent.execute",
        "agent.execute",
        "agent",
    )


def test_real_agents_register():
    manager = build_manager()

    assert manager.list_agents() == [
        "coding",
        "data",
        "research",
    ]


def test_real_agents_start_running():
    manager = build_manager()

    for name in manager.list_agents():
        assert (
            manager.control(name).state
            == AgentState.RUNNING
        )


def test_coding_agent_execution():
    manager = build_manager()

    result = manager.execute(
        "coding",
        "create a KAIRO module",
        context=execution_context(manager),
    )

    assert result.status == "UNAVAILABLE"
    assert result.agent == "coding"


def test_data_agent_execution():
    manager = build_manager()

    result = manager.execute(
        "data",
        "process KAIRO data",
        context=execution_context(manager),
    )

    assert result.status == "UNAVAILABLE"
    assert result.agent == "data"


def test_research_agent_execution():
    manager = build_manager()

    result = manager.execute(
        "research",
        "research KAIRO architecture",
        context=execution_context(manager),
    )

    assert result.status == "UNAVAILABLE"
    assert result.agent == "research"


def test_pause_blocks_real_agent():
    manager = build_manager()

    manager.pause("coding")

    assert (
        manager.control("coding").state
        == AgentState.PAUSED
    )

    try:
        manager.execute(
            "coding",
            "this must be blocked",
            context=execution_context(manager),
        )
    except Exception as exc:
        assert "not RUNNING" in str(exc)
    else:
        raise AssertionError(
            "Paused agent was allowed to execute."
        )


def test_stop_blocks_real_agent():
    manager = build_manager()

    manager.stop("data")

    assert (
        manager.control("data").state
        == AgentState.STOPPED
    )

    try:
        manager.execute(
            "data",
            "this must be blocked",
            context=execution_context(manager),
        )
    except Exception as exc:
        assert "not RUNNING" in str(exc)
    else:
        raise AssertionError(
            "Stopped agent was allowed to execute."
        )


def test_real_agents_health():
    manager = build_manager()

    manager.execute(
        "coding",
        "health test",
        context=execution_context(manager),
    )

    manager.execute(
        "data",
        "health test",
        context=execution_context(manager),
    )

    manager.execute(
        "research",
        "health test",
        context=execution_context(manager),
    )

    health = manager.health()

    assert health["status"] == "DEGRADED"
    assert health["count"] == 3

    assert health["execution_counts"] == {
        "coding": 1,
        "data": 1,
        "research": 1,
    }

    assert health["last_status"] == {
        "coding": "UNAVAILABLE",
        "data": "UNAVAILABLE",
        "research": "UNAVAILABLE",
    }