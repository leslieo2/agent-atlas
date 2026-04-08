from __future__ import annotations

from typing import Protocol
from uuid import UUID


class RunExecutionPayload(Protocol):
    def model_dump(self, *, mode: str) -> dict[str, object]: ...


class ExecutionJobPort(Protocol):
    def enqueue_run_execution(self, run_spec: RunExecutionPayload, *, job_id: str) -> None: ...

    def enqueue_experiment_execution(self, experiment_id: UUID) -> None: ...

    def enqueue_experiment_aggregation(self, experiment_id: UUID) -> None: ...


__all__ = ["ExecutionJobPort", "RunExecutionPayload"]
