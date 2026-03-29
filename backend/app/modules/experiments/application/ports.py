from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.modules.experiments.domain.models import (
    ExperimentRecord,
    RunEvaluationRecord,
)
from app.modules.runs.domain.models import RunRecord, RunSpec, TrajectoryStep
from app.modules.shared.domain.enums import RunStatus
from pydantic import BaseModel


class ExecutorCapability(BaseModel):
    backend: str
    production_ready: bool
    supports_cancel: bool
    supports_sync: bool


class ExecutorSubmission(BaseModel):
    backend: str
    submission_id: str


class ExecutorSyncResult(BaseModel):
    run_id: UUID
    backend: str
    status: RunStatus


class ExperimentRepository(Protocol):
    def list(self) -> list[ExperimentRecord]: ...

    def get(self, experiment_id: str | UUID) -> ExperimentRecord | None: ...

    def save(self, experiment: ExperimentRecord) -> None: ...


class RunEvaluationRepository(Protocol):
    def list_for_experiment(self, experiment_id: str | UUID) -> list[RunEvaluationRecord]: ...

    def get_by_run(self, run_id: str | UUID) -> RunEvaluationRecord | None: ...

    def save(self, record: RunEvaluationRecord) -> None: ...

    def delete_for_experiment(self, experiment_id: str | UUID) -> None: ...


class RunRepository(Protocol):
    def get(self, run_id: str | UUID) -> RunRecord | None: ...

    def list(self) -> list[RunRecord]: ...

    def save(self, run: RunRecord) -> None: ...


class TrajectoryRepository(Protocol):
    def list_for_run(self, run_id: str | UUID) -> list[TrajectoryStep]: ...

    def append(self, step: TrajectoryStep) -> None: ...


class ExecutorPort(Protocol):
    def submit(self, run_spec: RunSpec) -> ExecutorSubmission: ...

    def cancel(self, run_id: str | UUID) -> bool: ...

    def sync(self, run_id: str | UUID) -> ExecutorSyncResult | None: ...

    def capabilities(self) -> list[ExecutorCapability]: ...
