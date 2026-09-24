from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = (
    Path(__file__).resolve().parents[2]
)

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(PROJECT_ROOT),
    )


from UI.Command_Center.command_center import (
    CommandCenter,
)

from UI.Dashboard.dashboard import (
    Dashboard,
)


class FakeCore:

    def status(self):
        return {
            "system": "KAIRO",
            "version": "V2",
            "core": "ONLINE",
            "mode": "DEVELOPMENT",
            "active_tasks": 0,
        }


    def health(self):
        return {
            "system": "KAIRO",
            "core": "ONLINE",
        }


    def list_agents(self):
        return [
            "ResearchAgent",
            "CodingAgent",
        ]


    def events(self, limit=50):
        return [
            {
                "event": "TEST",
                "status": "OK",
            }
        ][:limit]


    def create_task(self, name):
        return {
            "id": "task-1",
            "name": name,
            "status": "PENDING",
        }


    def respond(self, message):
        return f"Echo: {message}"


class FakeSecurity:

    def authorize(
        self,
        identity_id,
        permission,
    ):
        return identity_id == "operator"


def make_center():

    return CommandCenter(
        core=FakeCore(),
        security=FakeSecurity(),
    )


def test_router():

    center = make_center()

    commands = center.router.commands()

    assert "status" in commands
    assert "health" in commands
    assert "agents" in commands
    assert "events" in commands
    assert "task" in commands
    assert "chat" in commands


def test_status_authorized():

    center = make_center()

    result = center.execute(
        "status",
        identity_id="operator",
    )

    assert result["core"] == "ONLINE"


def test_status_denied():

    center = make_center()

    result = center.execute(
        "status",
        identity_id="guest",
    )

    assert result["status"] == "DENIED"


def test_health():

    center = make_center()

    result = center.execute(
        "health",
        identity_id="operator",
    )

    assert result["core"] == "ONLINE"


def test_agents():

    center = make_center()

    result = center.execute(
        "agents",
        identity_id="operator",
    )

    assert result["count"] == 2


def test_events():

    center = make_center()

    result = center.execute(
        "events",
        identity_id="operator",
    )

    assert result["count"] == 1


def test_task():

    center = make_center()

    result = center.execute(
        "task",
        identity_id="operator",
        name="Build KAIRO",
    )

    assert result["status"] == "CREATED"
    assert (
        result["task"]["status"]
        == "PENDING"
    )


def test_chat():

    center = make_center()

    result = center.execute(
        "chat",
        identity_id="operator",
        message="hello",
    )

    assert result["status"] == "COMPLETED"
    assert "hello" in result["response"]


def test_dashboard():

    center = make_center()

    dashboard = Dashboard(center)

    result = dashboard.summary(
        identity_id="operator"
    )

    assert result["core"] == "ONLINE"
    assert result["agent_count"] == 2
    assert result["event_count"] == 1


def test_dashboard_health():

    center = make_center()

    dashboard = Dashboard(center)

    result = dashboard.health()

    assert result["status"] == "ONLINE"
