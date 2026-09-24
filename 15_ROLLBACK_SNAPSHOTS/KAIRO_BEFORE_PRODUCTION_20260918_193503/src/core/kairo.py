"""KAIRO V1 Core runtime."""

from __future__ import annotations

from datetime import datetime


class KairoCore:
    """Minimal interactive KAIRO core."""

    def __init__(self) -> None:
        self.name = "KAIRO"
        self.version = "V1"
        self.started_at = datetime.now()

    def status(self) -> dict[str, str]:
        return {
            "system": self.name,
            "version": self.version,
            "core": "ONLINE",
            "mode": "DEVELOPMENT",
            "security": "ACTIVE",
        }

    def respond(self, message: str) -> str:
        message = message.strip()

        if not message:
            return "Please give me a command or question."

        lowered = message.lower()

        if lowered in {"hello", "hi", "hey"}:
            return "Hello. KAIRO V1 is online. How can I help?"

        if "status" in lowered:
            status = self.status()
            return (
                f"{status['system']} {status['version']} | "
                f"Core: {status['core']} | "
                f"Security: {status['security']}"
            )

        if lowered in {"exit", "quit"}:
            return "__EXIT__"

        return f"I received: {message}"