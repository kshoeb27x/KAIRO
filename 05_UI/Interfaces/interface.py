from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass
class InterfaceRequest:

    command: str
    identity_id: str | None = None
    args: tuple[Any, ...] = ()
    kwargs: dict[str, Any] | None = None


@dataclass
class InterfaceResponse:

    status: str
    data: Any
    error: str | None = None


class CommandInterface(Protocol):

    def execute(
        self,
        request: InterfaceRequest,
    ) -> InterfaceResponse:
        ...
