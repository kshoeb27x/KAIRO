from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass
class InterfaceRequest:
    command: str
    payload: dict[str, Any]


@dataclass
class InterfaceResponse:
    status: str
    result: Any


class CommandInterface(Protocol):

    def handle(
        self,
        request: InterfaceRequest,
    ) -> InterfaceResponse:
        ...
