from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.modules.evals.application.ports import (
    DatasetSourcePort,
    EvalJobRepository,
    EvalRunGatewayPort,
    EvalSampleResultRepository,
)
from app.modules.evals.domain.models import EvalJobStatus
from app.modules.evals.domain.policies import EvalJobAggregate
from app.modules.evals.domain.scoring import evaluate_sample
from app.modules.shared.application.ports import TaskQueuePort
from app.modules.shared.domain.enums import RunStatus
from app.modules.shared.domain.tasks import QueuedTask, TaskType


@dataclass(frozen=True)
class EvalFailureDetails:
    code: str
    message: str


class EvalExecutionService:
    def __init__(
        self,
        eval_job_repository: EvalJobRepository,
        dataset_source: DatasetSourcePort,
        eval_run_gateway: EvalRunGatewayPort,
        task_queue: TaskQueuePort,
    ) -> None:
        self.eval_job_repository = eval_job_repository
        self.dataset_source = dataset_source
        self.eval_run_gateway = eval_run_gateway
        self.task_queue = task_queue

    def execute_job(self, eval_job_id: UUID) -> None:
        job = self.eval_job_repository.get(eval_job_id)
        if job is None:
            return
        dataset = self.dataset_source.get(job.dataset)
        if dataset is None:
            failed = EvalJobAggregate.load(job).mark_failed(
                error_code="runner_bootstrap",
                error_message=f"dataset '{job.dataset}' was not found",
            )
            self.eval_job_repository.save(failed)
            return

        if job.status == EvalJobStatus.QUEUED:
            job = EvalJobAggregate.load(job).mark_running()
            self.eval_job_repository.save(job)

        for sample in dataset.samples:
            self.eval_run_gateway.create_eval_run(job, sample)

        self.task_queue.enqueue(
            QueuedTask(
                task_type=TaskType.EVAL_AGGREGATION,
                target_id=job.eval_job_id,
                payload={"eval_job_id": str(job.eval_job_id)},
            )
        )


class EvalAggregationService:
    def __init__(
        self,
        eval_job_repository: EvalJobRepository,
        sample_result_repository: EvalSampleResultRepository,
        dataset_source: DatasetSourcePort,
        eval_run_gateway: EvalRunGatewayPort,
        task_queue: TaskQueuePort,
    ) -> None:
        self.eval_job_repository = eval_job_repository
        self.sample_result_repository = sample_result_repository
        self.dataset_source = dataset_source
        self.eval_run_gateway = eval_run_gateway
        self.task_queue = task_queue

    def refresh_job(self, eval_job_id: UUID) -> None:
        job = self.eval_job_repository.get(eval_job_id)
        if job is None:
            return
        dataset = self.dataset_source.get(job.dataset)
        if dataset is None:
            failed = EvalJobAggregate.load(job).mark_failed(
                error_code="runner_bootstrap",
                error_message=f"dataset '{job.dataset}' was not found",
            )
            self.eval_job_repository.save(failed)
            return

        runs = self.eval_run_gateway.list_eval_runs(eval_job_id)
        if len(runs) < len(dataset.samples) or any(
            run.status in {RunStatus.QUEUED, RunStatus.RUNNING} for run in runs
        ):
            self.task_queue.enqueue(
                QueuedTask(
                    task_type=TaskType.EVAL_AGGREGATION,
                    target_id=job.eval_job_id,
                    payload={"eval_job_id": str(job.eval_job_id)},
                )
            )
            return

        run_by_sample = {run.dataset_sample_id: run for run in runs}
        self.sample_result_repository.delete_for_job(eval_job_id)
        results = []
        for sample in dataset.samples:
            run = run_by_sample.get(sample.sample_id)
            if run is None:
                continue
            result = evaluate_sample(
                sample=sample,
                run=run,
                scoring_mode=job.scoring_mode,
                eval_job_id=job.eval_job_id,
            )
            self.sample_result_repository.save(result)
            results.append(result)

        completed = EvalJobAggregate.load(job).complete(results)
        self.eval_job_repository.save(completed)
