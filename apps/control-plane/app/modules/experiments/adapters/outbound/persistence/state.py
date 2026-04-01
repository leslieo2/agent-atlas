from __future__ import annotations

from typing import cast
from uuid import UUID

from app.db.persistence import StatePersistence
from app.infrastructure.repositories.common import persistence, to_uuid
from app.modules.experiments.domain.models import ExperimentRecord, RunEvaluationRecord

state_persistence = cast(StatePersistence, persistence)


class StateExperimentRepository:
    def list(self) -> list[ExperimentRecord]:
        return state_persistence.list_experiments()

    def get(self, experiment_id: str | UUID) -> ExperimentRecord | None:
        return state_persistence.get_experiment(to_uuid(experiment_id))

    def save(self, experiment: ExperimentRecord) -> None:
        state_persistence.save_experiment(experiment)


class StateRunEvaluationRepository:
    def list_for_experiment(self, experiment_id: str | UUID) -> list[RunEvaluationRecord]:
        return state_persistence.list_run_evaluations(to_uuid(experiment_id))

    def get_by_run(self, run_id: str | UUID) -> RunEvaluationRecord | None:
        return state_persistence.get_run_evaluation_by_run(to_uuid(run_id))

    def save(self, record: RunEvaluationRecord) -> None:
        state_persistence.save_run_evaluation(record)

    def delete_for_experiment(self, experiment_id: str | UUID) -> None:
        state_persistence.delete_run_evaluations(to_uuid(experiment_id))
