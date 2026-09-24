from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
UI_ROOT = PROJECT_ROOT / "05_UI"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(PROJECT_ROOT),
    )

if str(UI_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(UI_ROOT),
    )


from Command_Center.command_center import CommandCenter
from Dashboard.dashboard import Dashboard


class FakeCore:

    def __init__(self) -> None:
        self.created_tasks = []

    def status(self) -> dict:

        return {
            "system": "KAIRO",
            "version": "V2",
            "core": "ONLINE",
        }

    def health(self) -> dict:

        return {
            "system": "KAIRO",
            "health": "PASS",
        }

    def list_agents(self) -> list[str]:

        return [
            "Research",
            "Coding",
            "Data",
        ]

    def events(
        self,
        limit: int = 50,
    ) -> list[dict]:

        events = [
            {
                "event": "SYSTEM_STARTED",
                "timestamp": "now",
            }
        ]

        return events[:limit]

    def create_task(
        self,
        name: str,
    ) -> dict:

        self.created_tasks.append(
            name
        )

        return {
            "status": "CREATED",
            "name": name,
        }

    def respond(
        self,
        message: str,
    ) -> str:

        return f"echo:{message}"


class FakeSecurity:

    def __init__(
        self,
        allowed: bool = True,
    ) -> None:

        self.allowed = allowed
        self.calls = []

    def authorize(
        self,
        identity_id: str,
        permission: str,
    ) -> dict:

        self.calls.append(
            {
                "identity_id": identity_id,
                "permission": permission,
            }
        )

        return {
            "allowed": self.allowed,
        }


def test_status():

    center = CommandCenter(
        FakeCore()
    )

    result = center.execute(
        "status"
    )

    assert result["system"] == "KAIRO"


def test_health():

    center = CommandCenter(
        FakeCore()
    )

    result = center.execute(
        "health"
    )

    assert result["health"] == "PASS"


def test_agents():

    center = CommandCenter(
        FakeCore()
    )

    result = center.execute(
        "agents"
    )

    assert "Research" in result
    assert "Coding" in result


def test_events():

    center = CommandCenter(
        FakeCore()
    )

    result = center.execute(
        "events",
        limit=10,
    )

    assert len(result) == 1


def test_task():

    core = FakeCore()

    center = CommandCenter(
        core
    )

    result = center.execute(
        "task",
        name="Test Task",
    )

    assert result["status"] == "CREATED"
    assert "Test Task" in core.created_tasks


def test_chat():

    center = CommandCenter(
        FakeCore()
    )

    result = center.execute(
        "chat",
        message="hello",
    )

    assert result == "echo:hello"


def test_command_list():

    center = CommandCenter(
        FakeCore()
    )

    commands = center.router.commands()

    assert "status" in commands
    assert "health" in commands
    assert "agents" in commands
    assert "events" in commands
    assert "task" in commands
    assert "chat" in commands


def test_security_allows():

    security = FakeSecurity(
        True
    )

    center = CommandCenter(
        core=FakeCore(),
        security=security,
    )

    result = center.execute(
        "status",
        identity_id="user-1",
    )

    assert result["system"] == "KAIRO"
    assert len(
        security.calls
    ) == 1


def test_security_denies():

    security = FakeSecurity(
        False
    )

    center = CommandCenter(
        core=FakeCore(),
        security=security,
    )

    result = center.execute(
        "status",
        identity_id="user-1",
    )

    assert result["status"] == "DENIED"


def test_dashboard():

    center = CommandCenter(
        FakeCore()
    )

    dashboard = Dashboard(
        center
    )

    result = dashboard.summary()

    assert result["system"] == "KAIRO"
    assert result["agent_count"] == 3
    assert result["event_count"] == 1
