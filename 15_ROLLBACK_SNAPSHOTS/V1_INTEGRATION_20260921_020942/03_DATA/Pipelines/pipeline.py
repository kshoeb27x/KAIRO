from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable


@dataclass
class PipelineResult:
    name: str
    status: str
    output: Any
    started_at: str
    completed_at: str


class DataPipeline:

    def __init__(
        self,
        name: str,
        steps: list[Callable[[Any], Any]] | None = None,
    ) -> None:

        self.name = name
        self.steps = steps or []

    def add_step(
        self,
        step: Callable[[Any], Any],
    ) -> None:

        self.steps.append(step)

    def run(
        self,
        data: Any,
    ) -> PipelineResult:

        started = datetime.now().isoformat()

        try:
            output = data

            for step in self.steps:
                output = step(output)

            return PipelineResult(
                name=self.name,
                status="COMPLETED",
                output=output,
                started_at=started,
                completed_at=datetime.now().isoformat(),
            )

        except Exception as exc:

            return PipelineResult(
                name=self.name,
                status="FAILED",
                output=str(exc),
                started_at=started,
                completed_at=datetime.now().isoformat(),
            )
