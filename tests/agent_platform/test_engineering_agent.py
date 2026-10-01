from __future__ import annotations

import json
import sys
from importlib import import_module
from pathlib import Path
from typing import Any

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(PROJECT_ROOT / "02_AGENTS") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "02_AGENTS"))

AgentAuthority = import_module("02_AGENTS.authority").AgentAuthority
AgentManager = import_module("02_AGENTS.manager").AgentManager
AgentPermission = import_module("02_AGENTS.authority").Permission
AuthorityLevel = import_module(
    "06_SECURITY.Authority.authority"
).AuthorityLevel
RuntimeManager = import_module(
    "07_RUNTIME.runtime_manager"
).RuntimeManager
EngineeringAgent = import_module(
    "Engineering.engineering_agent"
).EngineeringAgent
SecurityManager = import_module(
    "06_SECURITY.security_manager"
).SecurityManager
EngineeringTool = import_module(
    "04_TOOLS.Engineering.tool"
).EngineeringTool
ToolManager = import_module("04_TOOLS.manager").ToolManager
KairoSystem = import_module(
    "src.kairo_system"
).KairoSystem


ENGINEERING_PERMISSIONS = (
    "engineering.inspect",
    "engineering.plan",
    "engineering.modify",
    "engineering.modify_tests",
    "engineering.test",
    "engineering.checkpoint",
    "engineering.rollback",
)

AGENT_AUTHORITY = AgentAuthority(
    agent_name="engineering",
    permissions=frozenset({
        AgentPermission.EXECUTE,
        AgentPermission.ENGINEERING_INSPECT,
        AgentPermission.ENGINEERING_PLAN,
        AgentPermission.ENGINEERING_MODIFY,
        AgentPermission.ENGINEERING_MODIFY_TESTS,
        AgentPermission.ENGINEERING_TEST,
        AgentPermission.ENGINEERING_CHECKPOINT,
        AgentPermission.ENGINEERING_ROLLBACK,
        AgentPermission.FILESYSTEM_WRITE,
        AgentPermission.PROCESS_EXECUTE,
        AgentPermission.CREATE_TASK,
    }),
)


class RepairProposalBackend:
    def __init__(self) -> None:
        self.attempts: list[int] = []

    def generate(self, prompt: str, context: Any) -> str:
        request = json.loads(prompt)
        self.attempts.append(request["attempt"])
        source = next(
            item
            for item in request["project_map"]["file_details"]
            if item["path"] == "answer.py"
        )
        fixed_value = 3 if request["attempt"] == 1 else 2
        return json.dumps({
            "summary": "Repair the answer implementation to satisfy its test.",
            "changes": [{
                "path": "answer.py",
                "expected_sha256": source["sha256"],
                "content": f"def answer():\n    return {fixed_value}\n",
            }],
            "completion_criteria": [
                "The discovered pytest suite passes.",
                "Python compilation succeeds.",
            ],
            "dependencies": [],
            "implementation_tasks": [
                "Update the answer implementation.",
            ],
            "validation_requirements": [
                "Run the discovered pytest suite.",
                "Compile Python files.",
            ],
            "risks": [],
        })


def create_environment(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    grant_filesystem_write: bool = True,
    grant_checkpoint: bool = True,
    command_runner=None,
    connect_runtime: bool = False,
) -> tuple[AgentManager, SecurityManager, Any]:
    monkeypatch.setenv(
        "KAIRO_AUDIT_DB",
        str(tmp_path / "audit.sqlite3"),
    )
    security = SecurityManager()
    security.identity.create("engineering-user", "Engineering User")
    security.authority.assign(
        "engineering-user",
        AuthorityLevel.USER,
    )
    for permission in (
        "agent.execute",
        "tool.invoke",
        "runtime.execute",
        "runtime.task.create",
        "runtime.task.read",
        "process.execute",
        *(
            permission
            for permission in ENGINEERING_PERMISSIONS
            if grant_checkpoint or permission != "engineering.checkpoint"
        ),
    ):
        security.permissions.grant("engineering-user", permission)
    if grant_filesystem_write:
        security.permissions.grant(
            "engineering-user",
            "filesystem.write",
        )

    security.identity.create("engineering-approver", "Engineering Approver")
    security.authority.assign(
        "engineering-approver",
        AuthorityLevel.ADMIN,
    )
    security.permissions.grant(
        "engineering-approver",
        "security.approve",
    )
    security.register_agent(
        "engineering",
        (
            *ENGINEERING_PERMISSIONS,
            "filesystem.write",
            "process.execute",
            "runtime.task.create",
        ),
    )
    security.sandbox.allow_filesystem_write = True
    security.sandbox.allow_process_execution = True

    def approve(operation_context: Any) -> str:
        return security.approve(
            operation_context,
            "engineering-approver",
        )

    runtime = RuntimeManager(security) if connect_runtime else None
    agent = EngineeringAgent(
        security=security,
        repository_root=tmp_path / "repo",
        proposal_backend=RepairProposalBackend(),
        approval_provider=approve,
        runtime=runtime,
        command_runner=command_runner,
    )
    manager = AgentManager(
        security=security,
        runtime=runtime,
    )
    manager.register(agent, AGENT_AUTHORITY)
    context = security.context(
        "engineering-user",
        "agent.execute",
        "agent.execute",
        "engineering",
    )
    return manager, security, context


def write_failing_project(root: Path) -> None:
    (root / "tests").mkdir(parents=True)
    (root / "answer.py").write_text(
        "def answer():\n    return 1\n",
        encoding="utf-8",
    )
    (root / "tests" / "test_answer.py").write_text(
        "from answer import answer\n\n"
        "def test_answer():\n"
        "    assert answer() == 2\n",
        encoding="utf-8",
    )


def test_engineering_agent_discovers_plans_repairs_and_verifies(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repo"
    repository.mkdir()
    write_failing_project(repository)
    manager, security, context = create_environment(
        monkeypatch,
        tmp_path,
    )

    result = manager.execute(
        "engineering",
        "Fix the failing answer test.",
        context=context,
    )

    assert result.status == "COMPLETED"
    assert (repository / "answer.py").read_text(encoding="utf-8") == (
        "def answer():\n    return 2\n"
    )
    assert result.result["status"] == "COMPLETED"
    assert result.result["result"]["tests"]["status"] == "PASS"
    assert result.result["result"]["tests"]["tests_discovered"] == 1
    assert result.result["result"]["compile"]["status"] == "PASS"
    assert result.result["result"]["imports"]["status"] == "PASS"
    assert result.result["result"]["files_changed"] == ["answer.py", "answer.py"]
    plan = result.result["result"]["plan"]
    assert plan["dependencies"] == []
    assert plan["implementation_tasks"] == [
        "Update the answer implementation.",
    ]
    assert plan["validation_requirements"] == [
        "Run the discovered pytest suite.",
        "Compile Python files.",
    ]
    assert plan["completion_criteria"]
    assert "tests/test_answer.py" in (
        result.result["result"]["project_map"]["groups"]["tests"]
    )
    assert len(manager.get("engineering").proposal_backend.attempts) == 2
    assert any(
        entry["event"] == "ENGINEERING_CHECKPOINT"
        and entry["status"] == "VERIFIED"
        for entry in security.audit.recent()
    )
    assert any(
        entry["event"] == "AUTHORIZATION"
        and entry["action"] == "sandbox.engineering.modify"
        and entry["details"]["resource"] == str(repository / "answer.py")
        for entry in security.audit.recent()
    )


def test_engineering_agent_creates_and_completes_runtime_task(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repo"
    repository.mkdir()
    write_failing_project(repository)
    manager, security, context = create_environment(
        monkeypatch,
        tmp_path,
        connect_runtime=True,
    )

    result = manager.execute(
        "engineering",
        "Fix the failing answer test.",
        context=context,
    )

    assert result.status == "COMPLETED"
    read_context = security.context(
        "engineering-user",
        "runtime.task.read",
        "task.list",
        "tasks",
    )
    tasks = manager.runtime.tasks.list_tasks(read_context)
    assert len(tasks) == 1
    assert tasks[0]["name"] == "Engineering: Fix the failing answer test."
    assert tasks[0]["status"] == "COMPLETED"


def test_engineering_objective_executes_through_tool_manager(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repo"
    repository.mkdir()
    write_failing_project(repository)
    manager, security, context = create_environment(
        monkeypatch,
        tmp_path,
    )
    tools = ToolManager(security)
    tools.register(
        EngineeringTool(
            manager,
            manager.get("engineering"),
        )
    )

    result = tools.execute(
        "engineering",
        "run",
        {"objective": "Fix the failing answer test."},
        context,
    )

    assert result.status == "COMPLETED"
    assert result.result["status"] == "COMPLETED"
    assert (repository / "answer.py").read_text(encoding="utf-8").endswith(
        "return 2\n"
    )


def test_engineering_agent_can_rollback_a_verified_checkpoint(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repo"
    repository.mkdir()
    write_failing_project(repository)
    original = (repository / "answer.py").read_bytes()
    manager, security, context = create_environment(
        monkeypatch,
        tmp_path,
    )

    result = manager.execute(
        "engineering",
        "Fix the failing answer test.",
        context=context,
    )
    checkpoint_id = result.result["result"]["plan"]["checkpoint_id"]
    rollback_result = manager.get("engineering").rollback(
        checkpoint_id,
        context,
    )

    assert rollback_result["status"] == "COMPLETED"
    assert (repository / "answer.py").read_bytes() == original
    last_result = manager.get("engineering").health()["last_result"]
    assert last_result["result"]["checkpoint_status"] == "ROLLED_BACK"
    checkpoint_events = [
        entry
        for entry in security.audit.recent()
        if entry["event"] == "ENGINEERING_CHECKPOINT"
        and entry["details"]["checkpoint_id"] == checkpoint_id
    ]
    assert [entry["status"] for entry in checkpoint_events] == [
        "VERIFIED",
        "ROLLED_BACK",
    ]
    rollback_events = [
        entry
        for entry in security.audit.recent()
        if entry["event"] == "ENGINEERING_ROLLBACK"
        and entry["details"]["checkpoint_id"] == checkpoint_id
    ]
    assert len(rollback_events) == 1
    assert rollback_events[0]["details"]["files_restored"] == ["answer.py"]


def test_engineering_agent_denies_missing_context(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repo"
    repository.mkdir()
    monkeypatch.setenv(
        "KAIRO_AUDIT_DB",
        str(tmp_path / "audit.sqlite3"),
    )
    agent = EngineeringAgent(
        security=SecurityManager(),
        repository_root=repository,
        proposal_backend=RepairProposalBackend(),
    )

    with pytest.raises(PermissionError, match="execution context"):
        agent.execute("Fix a defect.")


def test_engineering_agent_denies_missing_checkpoint_permission(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repo"
    repository.mkdir()
    write_failing_project(repository)
    manager, _, context = create_environment(
        monkeypatch,
        tmp_path,
        grant_checkpoint=False,
    )

    result = manager.execute(
        "engineering",
        "Fix the failing answer test.",
        context=context,
    )

    assert result.status == "DENIED"
    assert not (repository / "answer.py").read_text(
        encoding="utf-8"
    ).endswith("return 2\n")


def test_engineering_agent_blocks_emergency_stop(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repo"
    repository.mkdir()
    manager, security, context = create_environment(
        monkeypatch,
        tmp_path,
    )
    security.set_emergency_stopped(True)

    with pytest.raises(PermissionError):
        manager.execute(
            "engineering",
            "Fix a defect.",
            context=context,
        )

    assert not list(repository.glob("**/*"))


def test_failed_tests_do_not_report_completed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repo"
    repository.mkdir()
    write_failing_project(repository)
    manager, _, context = create_environment(
        monkeypatch,
        tmp_path,
    )
    backend = manager.get("engineering").proposal_backend

    def never_repair(prompt: str, execution_context: Any) -> str:
        request = json.loads(prompt)
        source = next(
            item
            for item in request["project_map"]["file_details"]
            if item["path"] == "answer.py"
        )
        return json.dumps({
            "summary": "A deliberately ineffective proposal.",
            "changes": [{
                "path": "answer.py",
                "expected_sha256": source["sha256"],
                "content": "def answer():\n    return 1\n",
            }],
            "completion_criteria": ["The answer test passes."],
            "dependencies": [],
            "implementation_tasks": [
                "Update the answer implementation.",
            ],
            "validation_requirements": [
                "Run the discovered pytest suite.",
            ],
            "risks": [],
        })

    backend.generate = never_repair
    result = manager.execute(
        "engineering",
        "Fix the failing answer test.",
        context=context,
    )

    assert result.status == "FAILED"
    assert result.result["status"] == "FAILED"
    assert result.result["result"]["tests"]["status"] == "FAIL"


def test_zero_tests_are_not_verified(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repo"
    repository.mkdir()
    (repository / "answer.py").write_text(
        "def answer():\n    return 1\n",
        encoding="utf-8",
    )
    manager, _, context = create_environment(
        monkeypatch,
        tmp_path,
    )

    result = manager.execute(
        "engineering",
        "Inspect the repository.",
        context=context,
    )

    assert result.status == "NOT_DISCOVERED"
    assert result.result["result"]["tests"]["tests_discovered"] == 0
    assert result.result["result"]["tests"]["status"] == "NOT_DISCOVERED"


def test_pytest_summary_counts_xfailed_and_xpassed_as_discovered() -> None:
    output = "2 passed, 1 xfailed, 1 xpassed in 0.10s"

    assert EngineeringAgent._pytest_count(output) == 4
    assert EngineeringAgent._pytest_summary_counts(output) == {
        "tests_passed": 2,
        "tests_failed": 0,
        "tests_errors": 0,
        "tests_skipped": 0,
        "tests_xfailed": 1,
        "tests_xpassed": 1,
    }


def test_blocked_test_process_is_reported_external(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repo"
    repository.mkdir()
    write_failing_project(repository)

    def blocked_runner(*args: Any, **kwargs: Any):
        raise PermissionError("terminal execution is blocked")

    manager, _, context = create_environment(
        monkeypatch,
        tmp_path,
        command_runner=blocked_runner,
    )
    result = manager.execute(
        "engineering",
        "Fix the failing answer test.",
        context=context,
    )

    assert result.status == "BLOCKED_EXTERNAL"
    assert result.result["result"]["status"] == "BLOCKED_EXTERNAL"
    assert "terminal execution is blocked" in result.result["next_action"]
    assert (
        "terminal execution is blocked"
        in result.result["result"]["tests"]["detail"]
    )


def test_engineering_agent_denies_modification_without_filesystem_permission(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repo"
    repository.mkdir()
    write_failing_project(repository)
    original = (repository / "answer.py").read_text(encoding="utf-8")
    manager, _, context = create_environment(
        monkeypatch,
        tmp_path,
        grant_filesystem_write=False,
    )

    result = manager.execute(
        "engineering",
        "Fix the failing answer test.",
        context=context,
    )

    assert result.status == "DENIED"
    assert (repository / "answer.py").read_text(encoding="utf-8") == original


def test_engineering_agent_respects_disabled_filesystem_capability(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repo"
    repository.mkdir()
    write_failing_project(repository)
    original = (repository / "answer.py").read_text(encoding="utf-8")
    manager, security, context = create_environment(
        monkeypatch,
        tmp_path,
    )
    security.sandbox.allow_filesystem_write = False

    result = manager.execute(
        "engineering",
        "Fix the failing answer test.",
        context=context,
    )

    assert result.status == "DENIED"
    assert (repository / "answer.py").read_text(encoding="utf-8") == original


def test_kairo_registers_engineering_agent_without_faking_backend(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv(
        "KAIRO_DATA_ROOT",
        str(tmp_path / "data"),
    )
    monkeypatch.setenv(
        "KAIRO_AUDIT_DB",
        str(tmp_path / "audit.sqlite3"),
    )
    system = KairoSystem()
    try:
        assert "engineering" in system.agents.list_agents()
        health = system.engineering_health()
        assert health["status"] == "BLOCKED_EXTERNAL"
        assert health["proposal_backend_configured"] is False
        assert system.health()["components"]["engineering"] == health
    finally:
        system.close()


def test_sandbox_configuration_is_explicit_and_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv(
        "KAIRO_AUDIT_DB",
        str(tmp_path / "audit.sqlite3"),
    )
    for name in (
        "KAIRO_SANDBOX_ALLOW_NETWORK",
        "KAIRO_SANDBOX_ALLOW_FILESYSTEM_WRITE",
        "KAIRO_SANDBOX_ALLOW_PROCESS_EXECUTION",
        "KAIRO_SANDBOX_ALLOW_SHELL",
    ):
        monkeypatch.delenv(name, raising=False)
    defaults = SecurityManager().sandbox.summary()
    assert defaults == {
        "allow_network": False,
        "allow_filesystem_write": False,
        "allow_process_execution": False,
        "allow_shell": False,
    }

    monkeypatch.setenv("KAIRO_SANDBOX_ALLOW_PROCESS_EXECUTION", "true")
    assert SecurityManager().sandbox.allow_process_execution is True
    monkeypatch.setenv("KAIRO_SANDBOX_ALLOW_PROCESS_EXECUTION", "sometimes")
    with pytest.raises(ValueError, match="must be set to a boolean"):
        SecurityManager()
