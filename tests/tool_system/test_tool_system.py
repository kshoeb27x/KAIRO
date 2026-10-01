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


tool_module = import_module(
    "04_TOOLS.tool"
)

manager_module = import_module(
    "04_TOOLS.manager"
)

browser_module = import_module(
    "04_TOOLS.Browser.tool"
)

computer_module = import_module(
    "04_TOOLS.Computer_Use.tool"
)

api_module = import_module(
    "04_TOOLS.API.tool"
)

mcp_module = import_module(
    "04_TOOLS.MCP.tool"
)

automation_module = import_module(
    "04_TOOLS.Automation.tool"
)


ToolDefinition = (
    tool_module.ToolDefinition
)

ToolRequest = (
    tool_module.ToolRequest
)

ToolManager = (
    manager_module.ToolManager
)
security_module = import_module(
    "06_SECURITY.security_manager"
)
authority_module = import_module(
    "06_SECURITY.Authority.authority"
)

BrowserTool = (
    browser_module.BrowserTool
)

ComputerUseTool = (
    computer_module.ComputerUseTool
)

APITool = (
    api_module.APITool
)

MCPTool = (
    mcp_module.MCPTool
)

AutomationTool = (
    automation_module.AutomationTool
)


def test_tool_definition():

    definition = ToolDefinition(
        name="demo",
        description="Demo tool",
        category="Test",
    )

    assert definition.name == "demo"
    assert definition.enabled is True


def test_manager_registration():

    manager = ToolManager()

    manager.register(
        BrowserTool()
    )

    assert manager.list_tools() == [
        "browser"
    ]


def test_tool_execution():

    security = security_module.SecurityManager()
    security.identity.create("tool-user", "Tool User")
    security.authority.assign(
        "tool-user",
        authority_module.AuthorityLevel.USER,
    )
    security.permissions.grant("tool-user", "network.read")
    context = security.context(
        "tool-user",
        "network.read",
        "tool.echo",
        "browser",
    )
    manager = ToolManager(security)

    manager.register(
        BrowserTool()
    )

    result = manager.execute(
        "browser",
        "echo",
        {
            "message": "hello"
        },
        context,
    )

    assert result.status == "COMPLETED"
    assert result.result["message"] == "hello"


def test_tool_failure():

    security = security_module.SecurityManager()
    security.identity.create("tool-user", "Tool User")
    security.authority.assign(
        "tool-user",
        authority_module.AuthorityLevel.USER,
    )
    security.permissions.grant("tool-user", "network.read")
    context = security.context(
        "tool-user",
        "network.read",
        "tool.unknown",
        "browser",
    )
    manager = ToolManager(security)

    manager.register(
        BrowserTool()
    )

    result = manager.execute(
        "browser",
        "unknown",
        context=context,
    )

    assert result.status == "FAILED"


def test_all_domains():

    manager = ToolManager()

    manager.register(
        BrowserTool()
    )

    manager.register(
        ComputerUseTool()
    )

    manager.register(
        APITool()
    )

    manager.register(
        MCPTool()
    )

    manager.register(
        AutomationTool()
    )

    assert manager.list_tools() == [
        "api",
        "automation",
        "browser",
        "computer_use",
        "mcp",
    ]

    assert manager.health()["count"] == 5


def test_permissions():

    browser = BrowserTool()

    result = browser.execute(
        "describe",
        {},
    )

    assert (
        "network.read"
        in result["permissions"]
    )
