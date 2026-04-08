from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.modules.agents.domain.models import PublishedAgent
from app.modules.experiments.domain.models import ExperimentRecord, RunEvaluationRecord
from app.modules.runs.application.ports import RunRepository, TrajectoryRepository
from app.modules.runs.domain.models import RunCreateInput, RunRecord


class ExperimentRepository(Protocol):
    def list(self) -> list[ExperimentRecord]: ...

    def get(self, experiment_id: str | UUID) -> ExperimentRecord | None: ...

    def save(self, experiment: ExperimentRecord) -> None: ...


class RunEvaluationRepository(Protocol):
    def list_for_experiment(self, experiment_id: str | UUID) -> list[RunEvaluationRecord]: ...

    def get_by_run(self, run_id: str | UUID) -> RunEvaluationRecord | None: ...

    def save(self, record: RunEvaluationRecord) -> None: ...

    def delete_for_experiment(self, experiment_id: str | UUID) -> None: ...


class RunSubmissionPort(Protocol):
    def submit(self, payload: RunCreateInput, agent: PublishedAgent) -> RunRecord: ...


__all__ = [
    "ExperimentRepository",
    "RunEvaluationRepository",
    "RunRepository",
    "RunSubmissionPort",
    "TrajectoryRepository",
]
