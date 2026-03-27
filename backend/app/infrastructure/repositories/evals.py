from __future__ import annotations

from uuid import UUID

from app.infrastructure.repositories.common import persistence, to_uuid
from app.modules.evals.domain.models import EvalJobRecord, EvalSampleResult


class StateEvalJobRepository:
    def get(self, eval_job_id: str | UUID) -> EvalJobRecord | None:
        return persistence.get_eval_job(to_uuid(eval_job_id))

    def list(self) -> list[EvalJobRecord]:
        return persistence.list_eval_jobs()

    def save(self, job: EvalJobRecord) -> None:
        persistence.save_eval_job(job)


class StateEvalSampleResultRepository:
    def list_for_job(self, eval_job_id: str | UUID) -> list[EvalSampleResult]:
        return persistence.list_eval_sample_results(to_uuid(eval_job_id))

    def save(self, result: EvalSampleResult) -> None:
        persistence.save_eval_sample_result(result)

    def delete_for_job(self, eval_job_id: str | UUID) -> None:
        persistence.delete_eval_sample_results(to_uuid(eval_job_id))


__all__ = [
    "StateEvalJobRepository",
    "StateEvalSampleResultRepository",
]
