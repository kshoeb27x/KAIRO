from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass
class AgentResult:
    agent: str
    task: str
    status: str
    result: Any


class Agent(Protocol):
    name: str

    def execute(self, task: str) -> AgentResult:
        ...
