from __future__ import annotations

from datetime import datetime
from typing import Any

from src.core.kairo_core import KairoCore
from src.integration import load_components


class KairoSystem:
    """Unified KAIRO V1 system composition layer."""

    VERSION = "V1"

    def __init__(self) -> None:
        self.name = "KAIRO"
        self.version = self.VERSION
        self.started_at = datetime.now()

        components = load_components()

        self.core = KairoCore()

        self.runtime = components["runtime"]()
        self.agents = components["agents"]()

        self.database = components["database"]()
        self.knowledge = components["knowledge"]()
        self.vector = components["vector"]()

        self.data = components["data_manager"](
            database=self.database,
            knowledge=self.knowledge,
            vector=self.vector,
        )

        self.security = components["security"]()

        # Tools remain outside this integration until their
        # existing implementation is wired into the system.
        self.tools = None

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
                    "status": "NOT_INTEGRATED",
                },
                "security": self.security.health(),
            },
        }

    def status(self) -> dict[str, Any]:
        return self.health()

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