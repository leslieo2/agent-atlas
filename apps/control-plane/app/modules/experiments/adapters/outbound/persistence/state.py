from __future__ import annotations

from uuid import UUID

from app.db.persistence import StatePersistence
from app.infrastructure.repositories.common import (
    StatePersistenceSource,
    resolve_state_persistence,
    to_uuid,
)
from app.modules.experiments.domain.models import ExperimentRecord, RunEvaluationRecord


class StateExperimentRepository:
    def __init__(self, persistence: StatePersistenceSource = None) -> None:
        self._persistence_source = persistence

    @property
    def _persistence(self) -> StatePersistence:
        return resolve_state_persistence(self._persistence_source)

    def list(self) -> list[ExperimentRecord]:
        return self._persistence.list_experiments()

    def get(self, experiment_id: str | UUID) -> ExperimentRecord | None:
        return self._persistence.get_experiment(to_uuid(experiment_id))

    def save(self, experiment: ExperimentRecord) -> None:
        self._persistence.save_experiment(experiment)


class StateRunEvaluationRepository:
    def __init__(self, persistence: StatePersistenceSource = None) -> None:
        self._persistence_source = persistence

    @property
    def _persistence(self) -> StatePersistence:
        return resolve_state_persistence(self._persistence_source)

    def list_for_experiment(self, experiment_id: str | UUID) -> list[RunEvaluationRecord]:
        return self._persistence.list_run_evaluations(to_uuid(experiment_id))

    def get_by_run(self, run_id: str | UUID) -> RunEvaluationRecord | None:
        return self._persistence.get_run_evaluation_by_run(to_uuid(run_id))

    def save(self, record: RunEvaluationRecord) -> None:
        self._persistence.save_run_evaluation(record)

    def delete_for_experiment(self, experiment_id: str | UUID) -> None:
        self._persistence.delete_run_evaluations(to_uuid(experiment_id))
