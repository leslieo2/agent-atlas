from __future__ import annotations

from uuid import UUID

from app.modules.evals.application.execution import EvalJobRecorder, EvalJobRunner
from app.modules.evals.application.ports import EvalJobRepository
from app.modules.evals.domain.models import EvalJob, EvalJobCreate
from app.modules.shared.application.ports import SchedulerPort


class EvalJobQueries:
    def __init__(self, eval_job_repository: EvalJobRepository) -> None:
        self.eval_job_repository = eval_job_repository

    def get_job(self, job_id: str | UUID) -> EvalJob | None:
        return self.eval_job_repository.get(job_id)


class EvalJobCommands:
    def __init__(
        self,
        eval_job_repository: EvalJobRepository,
        scheduler: SchedulerPort,
        runner: EvalJobRunner | None = None,
    ) -> None:
        self.eval_job_repository = eval_job_repository
        self.scheduler = scheduler
        self.runner = runner or EvalJobRunner(
            recorder=EvalJobRecorder(eval_job_repository=eval_job_repository),
        )

    def create_job(self, payload: EvalJobCreate) -> EvalJob:
        job = EvalJob(run_ids=payload.run_ids, dataset=payload.dataset)
        self.eval_job_repository.save(job)
        self.scheduler.submit(job.job_id, lambda: self._run_job(job.job_id, payload))
        return job

    def _run_job(self, job_id: UUID, payload: EvalJobCreate) -> None:
        self.runner.run(job_id, payload)
