from __future__ import annotations

from app.core.errors import AgentNotPublishedError, DatasetNotFoundError
from app.modules.evals.application.ports import (
    AgentLookupPort,
    DatasetSourcePort,
    EvalJobRepository,
    EvalSampleResultRepository,
)
from app.modules.evals.domain.models import EvalJobCreateInput, EvalJobRecord, EvalSampleResult
from app.modules.evals.domain.policies import EvalJobAggregate
from app.modules.shared.application.ports import TaskQueuePort
from app.modules.shared.domain.tasks import QueuedTask, TaskType


class EvalJobQueries:
    def __init__(
        self,
        eval_job_repository: EvalJobRepository,
        sample_result_repository: EvalSampleResultRepository,
    ) -> None:
        self.eval_job_repository = eval_job_repository
        self.sample_result_repository = sample_result_repository

    def list_jobs(self) -> list[EvalJobRecord]:
        return sorted(
            self.eval_job_repository.list(),
            key=lambda job: job.created_at,
            reverse=True,
        )

    def get_job(self, eval_job_id: str) -> EvalJobRecord | None:
        return self.eval_job_repository.get(eval_job_id)

    def list_samples(self, eval_job_id: str) -> list[EvalSampleResult]:
        return self.sample_result_repository.list_for_job(eval_job_id)


class EvalJobCommands:
    def __init__(
        self,
        eval_job_repository: EvalJobRepository,
        dataset_source: DatasetSourcePort,
        agent_lookup: AgentLookupPort,
        task_queue: TaskQueuePort,
    ) -> None:
        self.eval_job_repository = eval_job_repository
        self.dataset_source = dataset_source
        self.agent_lookup = agent_lookup
        self.task_queue = task_queue

    def create_job(self, payload: EvalJobCreateInput) -> EvalJobRecord:
        dataset = self.dataset_source.get(payload.dataset)
        if dataset is None:
            raise DatasetNotFoundError(payload.dataset)
        if not self.agent_lookup.exists(payload.agent_id):
            raise AgentNotPublishedError(payload.agent_id)

        job = EvalJobAggregate.create(payload, sample_count=len(dataset.samples))
        self.eval_job_repository.save(job)
        self.task_queue.enqueue(
            QueuedTask(
                task_type=TaskType.EVAL_EXECUTION,
                target_id=job.eval_job_id,
                payload={"eval_job_id": str(job.eval_job_id)},
            )
        )
        return job
