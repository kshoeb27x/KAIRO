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


runtime_module = import_module(
    "07_RUNTIME"
)

RuntimeManager = (
    runtime_module.RuntimeManager
)


def test_runtime_health():

    runtime = RuntimeManager()

    health = runtime.health()

    assert health["status"] == "ONLINE"
    assert health["runtime"]["status"] == "ONLINE"


def test_task_lifecycle():

    runtime = RuntimeManager()

    task = runtime.create_task(
        "demo"
    )

    assert task["status"] == "PENDING"

    assert (
        runtime.status()["active_tasks"]
        == 1
    )

    completed = runtime.complete_task(
        task["id"],
        {"ok": True},
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

    runtime = RuntimeManager()

    task = runtime.create_task(
        "failure"
    )

    failed = runtime.fail_task(
        task["id"],
        "demo error",
    )

    assert failed["status"] == "FAILED"

    assert (
        runtime.status()["failed_tasks"]
        == 1
    )


def test_execution():

    runtime = RuntimeManager()

    result = runtime.execute(
        "addition",
        lambda: 2 + 3,
    )

    assert result.status == "COMPLETED"
    assert result.result == 5

    assert (
        runtime.status()["completed_jobs"]
        == 1
    )


def test_execution_failure():

    runtime = RuntimeManager()

    def fail():
        raise RuntimeError("boom")

    result = runtime.execute(
        "failure",
        fail,
    )

    assert result.status == "FAILED"

    assert "boom" in result.error

    assert (
        runtime.status()["failed_jobs"]
        == 1
    )


def test_workflow():

    runtime = RuntimeManager()

    workflow = runtime.workflow(
        "demo-workflow"
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

    runtime = RuntimeManager()

    workflow = runtime.workflow(
        "broken-workflow"
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


def test_scheduler():

    runtime = RuntimeManager()

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
    )

    assert scheduled["enabled"] is True

    result = runtime.scheduler.run(
        scheduled["id"]
    )

    assert result == 1
    assert counter["value"] == 1

    jobs = runtime.scheduler.list_jobs()

    assert jobs[0]["run_count"] == 1


def test_events():

    runtime = RuntimeManager()

    runtime.create_task(
        "event-test"
    )

    events = runtime.events.recent()

    names = [
        event["name"]
        for event in events
    ]

    assert "RUNTIME_STARTED" in names
    assert "TASK_CREATED" in names
