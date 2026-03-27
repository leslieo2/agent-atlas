from __future__ import annotations

from app.modules.agents.domain.models import PublishedAgent
from app.modules.runs.application.ports import RunRepository
from app.modules.runs.domain.models import RunCreateInput, RunRecord, RunSpec
from app.modules.runs.domain.policies import RunAggregate
from app.modules.shared.application.ports import TaskQueuePort
from app.modules.shared.domain.tasks import QueuedTask, TaskType


class RunSubmissionService:
    def __init__(
        self,
        run_repository: RunRepository,
        task_queue: TaskQueuePort,
    ) -> None:
        self.run_repository = run_repository
        self.task_queue = task_queue

    def submit(self, payload: RunCreateInput, agent: PublishedAgent) -> RunRecord:
        spec = RunSpec(
            project=payload.project,
            dataset=payload.dataset,
            eval_job_id=payload.eval_job_id,
            dataset_sample_id=payload.dataset_sample_id,
            agent_id=payload.agent_id,
            model=agent.default_model,
            entrypoint=agent.entrypoint,
            agent_type=agent.adapter_kind(),
            input_summary=payload.input_summary,
            prompt=payload.prompt,
            tags=list(payload.tags),
            project_metadata={
                **payload.project_metadata,
                "agent_snapshot": agent.to_snapshot(),
            },
        )
        run = RunAggregate.create(spec)
        self.run_repository.save(run)
        self.task_queue.enqueue(
            QueuedTask(
                task_type=TaskType.RUN_EXECUTION,
                target_id=run.run_id,
                payload=spec.model_dump(mode="json"),
            )
        )
        return run
