from __future__ import annotations

from uuid import UUID

from app.infrastructure.repositories.common import state, to_uuid
from app.modules.datasets.domain.models import Dataset
from app.modules.evals.domain.models import EvalJob
from app.modules.replays.domain.models import ReplayResult


class StateDatasetRepository:
    def list(self) -> list[Dataset]:
        with state.lock:
            return list(state.datasets.values())

    def get(self, name: str) -> Dataset | None:
        with state.lock:
            return state.datasets.get(name)

    def save(self, dataset: Dataset) -> None:
        state.save_dataset(dataset)


class StateEvalJobRepository:
    def get(self, job_id: str | UUID) -> EvalJob | None:
        with state.lock:
            return state.eval_jobs.get(to_uuid(job_id))

    def save(self, job: EvalJob) -> None:
        state.save_eval_job(job)


class StateReplayRepository:
    def get(self, replay_id: str | UUID) -> ReplayResult | None:
        with state.lock:
            return state.replays.get(to_uuid(replay_id))

    def save(self, replay: ReplayResult) -> None:
        state.save_replay(replay)


__all__ = [
    "StateDatasetRepository",
    "StateEvalJobRepository",
    "StateReplayRepository",
]
