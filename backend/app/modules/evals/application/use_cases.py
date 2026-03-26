from __future__ import annotations

from uuid import UUID

from app.core.errors import UnsupportedOperationError
from app.modules.evals.application.ports import EvalJobRepository, EvalRunReader
from app.modules.evals.domain.models import EvalJob, EvalJobCreate
from app.modules.shared.application.ports import TaskQueuePort
from app.modules.shared.domain.tasks import QueuedTask, TaskType


class EvalJobQueries:
    def __init__(self, eval_job_repository: EvalJobRepository) -> None:
        self.eval_job_repository = eval_job_repository

    def get_job(self, job_id: str | UUID) -> EvalJob | None:
        return self.eval_job_repository.get(job_id)


class EvalJobCommands:
    def __init__(
        self,
        eval_job_repository: EvalJobRepository,
        task_queue: TaskQueuePort,
        run_repository: EvalRunReader,
    ) -> None:
        self.eval_job_repository = eval_job_repository
        self.task_queue = task_queue
        self.run_repository = run_repository

    def create_job(self, payload: EvalJobCreate) -> EvalJob:
        for run_id in payload.run_ids:
            run = self.run_repository.get(run_id)
            if run and run.agent_id:
                raise UnsupportedOperationError(
                    "eval is not supported for registered agent runs",
                    operation="eval",
                    run_id=str(run_id),
                    agent_id=run.agent_id,
                )
        job = EvalJob(run_ids=payload.run_ids, dataset=payload.dataset)
        self.eval_job_repository.save(job)
        self.task_queue.enqueue(
            QueuedTask(
                task_type=TaskType.EVAL_EXECUTION,
                target_id=job.job_id,
                payload=payload.model_dump(mode="json"),
            )
        )
        return job
