from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class SandboxPolicy:
    allow_network: bool = False
    allow_filesystem_write: bool = False
    allow_process_execution: bool = False
    allow_shell: bool = False

    def allows(
        self,
        capability: str,
    ) -> bool:

        mapping = {
            "network": self.allow_network,
            "filesystem_write": self.allow_filesystem_write,
            "process_execution": self.allow_process_execution,
            "shell": self.allow_shell,
        }

        return mapping.get(
            capability,
            False,
        )

    def summary(self) -> dict[str, Any]:
        return {
            "allow_network": self.allow_network,
            "allow_filesystem_write": self.allow_filesystem_write,
            "allow_process_execution": self.allow_process_execution,
            "allow_shell": self.allow_shell,
        }
