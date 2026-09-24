from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Callable


@dataclass
class ScheduledJob:
    id: int
    name: str
    interval_seconds: float
    enabled: bool = True
    last_run: str | None = None
    run_count: int = 0


class Scheduler:
    """Lightweight scheduler registry.

    This version registers and manually
    triggers jobs. Background scheduling
    can be added later.
    """

    def __init__(self) -> None:

        self._jobs: dict[
            int,
            ScheduledJob,
        ] = {}

        self._functions: dict[
            int,
            Callable[..., Any],
        ] = {}

        self._next_id = 1

    def schedule(
        self,
        name: str,
        interval_seconds: float,
        function: Callable[..., Any],
    ) -> dict[str, Any]:

        if interval_seconds <= 0:
            raise ValueError(
                "interval_seconds must be positive"
            )

        job = ScheduledJob(
            id=self._next_id,
            name=name,
            interval_seconds=interval_seconds,
        )

        self._jobs[job.id] = job
        self._functions[job.id] = function

        self._next_id += 1

        return asdict(job)

    def run(
        self,
        job_id: int,
    ) -> Any:

        job = self._jobs[job_id]

        if not job.enabled:
            raise RuntimeError(
                "Scheduled job is disabled"
            )

        function = self._functions[job_id]

        result = function()

        job.last_run = (
            datetime.now().isoformat()
        )

        job.run_count += 1

        return result

    def cancel(
        self,
        job_id: int,
    ) -> bool:

        job = self._jobs.get(job_id)

        if job is None:
            return False

        job.enabled = False

        return True

    def list_jobs(
        self,
    ) -> list[dict[str, Any]]:

        return [
            asdict(job)
            for job in self._jobs.values()
        ]

    def health(self) -> dict[str, Any]:

        return {
            "status": "ONLINE",
            "jobs": len(self._jobs),
            "enabled": sum(
                1
                for job in self._jobs.values()
                if job.enabled
            ),
        }
