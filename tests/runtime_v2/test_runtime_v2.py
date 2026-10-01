from __future__ import annotations

import sys
from pathlib import Path
from importlib import import_module

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(PROJECT_ROOT),
    )


runtime_module = import_module(
    "07_RUNTIME"
)

RuntimeManager = (
    runtime_module.RuntimeManager
)
SecurityManager = import_module(
    "06_SECURITY.security_manager"
).SecurityManager
AuthorityLevel = import_module(
    "06_SECURITY.Authority.authority"
).AuthorityLevel


def make_runtime(*permissions: str):
    security = SecurityManager()
    security.identity.create("runtime-user", "Runtime User")
    security.authority.assign("runtime-user", AuthorityLevel.USER)
    for permission in permissions:
        security.permissions.grant("runtime-user", permission)
    return RuntimeManager(security), security


def context(security, permission: str, resource: str = "runtime"):
    return security.context(
        "runtime-user",
        permission,
        permission,
        resource,
    )


def test_runtime_health():

    runtime = RuntimeManager()

    health = runtime.health()

    assert health["status"] == "ONLINE"
    assert health["runtime"]["status"] == "ONLINE"


def test_task_lifecycle():

    runtime, security = make_runtime(
        "runtime.task.create",
        "runtime.execute",
    )

    task = runtime.create_task(
        "demo",
        context(security, "runtime.task.create", "demo"),
    )

    assert task["status"] == "PENDING"

    assert (
        runtime.status()["active_tasks"]
        == 1
    )

    completed = runtime.complete_task(
        task["id"],
        {"ok": True},
        context(security, "runtime.execute", str(task["id"])),
    )

    assert (
        completed["status"]
        == "COMPLETED"
    )

    assert (
        runtime.status()["active_tasks"]
        == 0
    )

    assert (
        runtime.status()["completed_tasks"]
        == 1
    )


def test_task_failure():

    runtime, security = make_runtime(
        "runtime.task.create",
        "runtime.execute",
    )

    task = runtime.create_task(
        "failure",
        context(security, "runtime.task.create", "failure"),
    )

    failed = runtime.fail_task(
        task["id"],
        "demo error",
        context(security, "runtime.execute", str(task["id"])),
    )

    assert failed["status"] == "FAILED"

    assert (
        runtime.status()["failed_tasks"]
        == 1
    )


def test_execution():

    runtime, security = make_runtime("runtime.execute")

    result = runtime.execute(
        "addition",
        lambda: 2 + 3,
        context=context(security, "runtime.execute", "addition"),
    )

    assert result.status == "COMPLETED"
    assert result.result == 5

    assert (
        runtime.status()["completed_jobs"]
        == 1
    )


def test_execution_failure():

    runtime, security = make_runtime("runtime.execute")

    def fail():
        raise RuntimeError("boom")

    result = runtime.execute(
        "failure",
        fail,
        context=context(security, "runtime.execute", "failure"),
    )

    assert result.status == "FAILED"

    assert "boom" in result.error

    assert (
        runtime.status()["failed_jobs"]
        == 1
    )


def test_execution_retries_and_reports_attempts():
    runtime, security = make_runtime("runtime.execute")
    attempts = {"count": 0}

    def eventually_succeeds():
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise RuntimeError("retry")
        return "ok"

    result = runtime.execute(
        "retry",
        eventually_succeeds,
        max_attempts=3,
        context=context(security, "runtime.execute", "retry"),
    )

    assert result.status == "COMPLETED"
    assert result.result == "ok"
    assert result.attempts == 3
    assert attempts["count"] == 3


def test_workflow():

    runtime, security = make_runtime(
        "runtime.workflow.execute",
        "runtime.execute",
    )

    workflow = runtime.workflow(
        "demo-workflow",
        context(
            security,
            "runtime.workflow.execute",
            "demo-workflow",
        ),
    )

    workflow.add_step(
        "one",
        lambda: 1,
    )

    workflow.add_step(
        "two",
        lambda: 2,
    )

    result = workflow.run()

    assert result.status == "COMPLETED"
    assert result.results == [1, 2]

    assert (
        runtime.status()["completed_workflows"]
        == 1
    )


def test_workflow_failure():

    runtime, security = make_runtime(
        "runtime.workflow.execute",
        "runtime.execute",
    )

    workflow = runtime.workflow(
        "broken-workflow",
        context(
            security,
            "runtime.workflow.execute",
            "broken-workflow",
        ),
    )

    workflow.add_step(
        "one",
        lambda: 1,
    )

    def fail():
        raise ValueError("broken")

    workflow.add_step(
        "fail",
        fail,
    )

    result = workflow.run()

    assert result.status == "FAILED"
    assert "broken" in result.error

    assert (
        runtime.status()["failed_workflows"]
        == 1
    )


def test_workflow_rechecks_authorization_when_run():
    runtime, security = make_runtime(
        "runtime.workflow.execute",
        "runtime.execute",
    )
    workflow_context = context(
        security,
        "runtime.workflow.execute",
        "revoked-workflow",
    )
    workflow = runtime.workflow("revoked-workflow", workflow_context)
    invoked = []
    workflow.add_step("must-not-run", lambda: invoked.append(True))
    security.permissions.revoke(
        "runtime-user",
        "runtime.workflow.execute",
    )

    result = workflow.run()

    assert result.status == "FAILED"
    assert invoked == []
    assert runtime.status()["failed_workflows"] == 1


def test_scheduler():

    runtime, security = make_runtime(
        "runtime.schedule",
        "runtime.execute",
    )

    counter = {
        "value": 0
    }

    def job():

        counter["value"] += 1

        return counter["value"]

    scheduled = runtime.schedule(
        "counter",
        60,
        job,
        context=context(security, "runtime.schedule", "counter"),
    )

    assert scheduled["enabled"] is True

    result = runtime.scheduler.run(
        scheduled["id"],
        context=context(security, "runtime.execute", "counter"),
    )

    assert result.status == "COMPLETED"
    assert result.result == 1
    assert counter["value"] == 1

    jobs = runtime.scheduler.list_jobs()

    assert jobs[0]["run_count"] == 1


def test_direct_scheduler_access_requires_authorization_context():
    runtime, security = make_runtime(
        "runtime.schedule",
        "runtime.execute",
    )
    called = False

    def operation():
        nonlocal called
        called = True

    with pytest.raises(PermissionError):
        runtime.scheduler.schedule("direct", 60, operation)
    assert called is False

    scheduled = runtime.scheduler.schedule(
        "direct",
        60,
        operation,
        context=context(security, "runtime.schedule", "direct"),
    )
    with pytest.raises(PermissionError):
        runtime.scheduler.run(scheduled["id"])
    assert called is False

    runtime.scheduler.run(
        scheduled["id"],
        context=context(security, "runtime.execute", "direct"),
    )
    assert called is True
    with pytest.raises(PermissionError):
        runtime.scheduler.cancel(scheduled["id"])
    assert runtime.scheduler.cancel(
        scheduled["id"],
        context=context(security, "runtime.schedule", str(scheduled["id"])),
    )
    assert runtime.scheduler.list_jobs()[0]["enabled"] is False


def test_emergency_stop_blocks_queued_scheduler_work():
    runtime, security = make_runtime(
        "runtime.schedule",
        "runtime.execute",
        "runtime.emergency_stop",
    )
    called = False

    def operation():
        nonlocal called
        called = True

    scheduled = runtime.schedule(
        "queued",
        60,
        operation,
        context=context(security, "runtime.schedule", "queued"),
    )
    runtime.emergency_stop(
        context(security, "runtime.emergency_stop")
    )

    with pytest.raises(PermissionError):
        runtime.scheduler.run(
            scheduled["id"],
            context=context(security, "runtime.execute", "queued"),
        )
    assert called is False


def test_events():

    runtime, security = make_runtime("runtime.task.create")

    runtime.create_task(
        "event-test",
        context(security, "runtime.task.create", "event-test"),
    )

    events = runtime.events.recent()

    names = [
        event["name"]
        for event in events
    ]

    assert "RUNTIME_STARTED" in names
    assert "TASK_CREATED" in names
