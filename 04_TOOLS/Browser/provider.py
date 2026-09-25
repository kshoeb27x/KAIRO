from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class BrowserRequest:
    """Provider-neutral browser action."""

    action: str
    arguments: dict[str, Any] = field(default_factory=dict)


class BrowserProvider(Protocol):
    """Optional external browser automation contract."""

    def execute(self, request: BrowserRequest) -> Any:
        ...

    def health(self) -> dict[str, Any]:
        ...
