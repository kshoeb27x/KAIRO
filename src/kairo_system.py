from __future__ import annotations

from datetime import datetime
from importlib import import_module
from typing import Any

from src.core.kairo_core import KairoCore
from src.integration import load_components


APITool = import_module("04_TOOLS.API.tool").APITool
AutomationTool = import_module("04_TOOLS.Automation.tool").AutomationTool
BrowserTool = import_module("04_TOOLS.Browser.tool").BrowserTool
ComputerUseTool = import_module("04_TOOLS.Computer_Use.tool").ComputerUseTool
MCPTool = import_module("04_TOOLS.MCP.tool").MCPTool


class KairoSystem:
    """Unified KAIRO V1 system composition layer."""

    VERSION = "V1"

    def __init__(self) -> None:
        self.name = "KAIRO"
        self.version = self.VERSION
        self.started_at = datetime.now()

        components = load_components()

        self.runtime = components["runtime"]()
        self.core = KairoCore(runtime=self.runtime)
        self.agents = self.core.orchestrator.agents

        self.database = components["database"]()
        self.knowledge = components["knowledge"]()
        self.vector = components["vector"]()
        self.memory = components["memory"]()

        self.data = components["data_manager"](
            database=self.database,
            knowledge=self.knowledge,
            vector=self.vector,
            memory=self.memory,
        )

        self.security = components["security"]()

        tools_module = __import__("04_TOOLS.manager", fromlist=["ToolManager"])
        self.tools = tools_module.ToolManager()
        for tool in (
            BrowserTool(),
            ComputerUseTool(),
            APITool(),
            MCPTool(),
            AutomationTool(),
        ):
            self.tools.register(tool)

        self._status = "ONLINE"

    def health(self) -> dict[str, Any]:
        return {
            "system": self.name,
            "version": self.version,
            "status": self._status,
            "started_at": self.started_at.isoformat(),
            "components": {
                "core": self.core.health(),
                "runtime": self.runtime.health(),
                "agents": self.agents.health(),
                "data": self.data.health(),
                "tools": {
                    **self.tools.health(),
                },
                "security": self.security.health(),
            },
        }

    def status(self) -> dict[str, Any]:
        return self.health()

    def respond(self, message: str) -> str:
        return self.core.respond(message)

    def events(self, limit: int = 50) -> list[dict[str, Any]]:
        return self.core.events(limit)

    def component(self, name: str) -> Any:
        return getattr(self, name, None)

    def create_task(self, name: str) -> dict[str, Any]:
        return self.runtime.create_task(name)

    def execute_agent(
        self,
        name: str,
        task: str,
    ) -> Any:
        return self.agents.execute(name, task)

    def execute_tool(
        self,
        tool: str,
        action: str,
        arguments: dict[str, Any] | None = None,
    ) -> Any:
        return self.tools.execute(tool, action, arguments)