from __future__ import annotations

from typing import TYPE_CHECKING, Protocol
from uuid import UUID

if TYPE_CHECKING:
    from app.execution.contracts import ExecutionRunSpec


class ExecutionJobPort(Protocol):
    def enqueue_run_execution(self, run_spec: ExecutionRunSpec, *, job_id: str) -> None: ...

    def enqueue_experiment_execution(self, experiment_id: UUID) -> None: ...

    def enqueue_experiment_aggregation(self, experiment_id: UUID) -> None: ...


__all__ = ["ExecutionJobPort"]
