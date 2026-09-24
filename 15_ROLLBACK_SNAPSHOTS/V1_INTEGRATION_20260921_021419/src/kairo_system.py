from __future__ import annotations

from datetime import datetime
from typing import Any


class KairoSystem:
    """
    KAIRO V1 unified composition layer.

    This layer intentionally keeps service construction tolerant because
    individual KAIRO subsystems may expose different constructor contracts.
    Integration validation is responsible for proving which services are
    actually available.
    """

    VERSION = "V1"

    def __init__(
        self,
        core: Any = None,
        runtime: Any = None,
        agents: Any = None,
        data: Any = None,
        tools: Any = None,
        security: Any = None,
    ) -> None:
        self.name = "KAIRO"
        self.version = self.VERSION
        self.started_at = datetime.now()

        self.core = core
        self.runtime = runtime
        self.agents = agents
        self.data = data
        self.tools = tools
        self.security = security

        self._status = "ONLINE"

    def health(self) -> dict:
        return {
            "system": self.name,
            "version": self.version,
            "status": self._status,
            "started_at": self.started_at.isoformat(),
            "components": {
                "core": self.core is not None,
                "runtime": self.runtime is not None,
                "agents": self.agents is not None,
                "data": self.data is not None,
                "tools": self.tools is not None,
                "security": self.security is not None,
            },
        }

    def status(self) -> dict:
        return self.health()

    def component(self, name: str) -> Any:
        return getattr(self, name, None)
