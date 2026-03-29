from __future__ import annotations

from app.core.errors import AgentFrameworkMismatchError, AgentLoadFailedError
from app.modules.agents.domain.models import PublishedAgent
from app.modules.runs.application.ports import RunRepository
from app.modules.runs.domain.models import RunCreateInput, RunRecord, RunSpec
from app.modules.runs.domain.policies import RunAggregate
from app.modules.shared.application.ports import TaskQueuePort
from app.modules.shared.domain.tasks import QueuedTask, TaskType


def _resolve_submission_agent(agent: PublishedAgent) -> PublishedAgent:
    provenance = agent.provenance
    snapshot = provenance.published_agent_snapshot if provenance else None
    if snapshot is None:
        return agent

    try:
        published_snapshot = PublishedAgent.model_validate(snapshot)
    except Exception as exc:
        raise AgentLoadFailedError(
            "published agent is missing a valid snapshot",
            agent_id=agent.agent_id,
        ) from exc

    if published_snapshot.agent_id != agent.agent_id:
        raise AgentFrameworkMismatchError(
            "published agent snapshot does not match the stored agent identifier",
            agent_id=agent.agent_id,
            snapshot_agent_id=published_snapshot.agent_id,
        )

    if published_snapshot.framework != agent.framework:
        raise AgentFrameworkMismatchError(
            "published agent snapshot framework does not match stored agent metadata",
            agent_id=agent.agent_id,
            expected_framework=published_snapshot.framework,
            actual_framework=agent.framework,
        )

    if provenance and provenance.framework and provenance.framework != published_snapshot.framework:
        raise AgentFrameworkMismatchError(
            "published agent provenance framework does not match the published snapshot",
            agent_id=agent.agent_id,
            expected_framework=published_snapshot.framework,
            actual_framework=provenance.framework,
        )

    return published_snapshot


class RunSubmissionService:
    def __init__(
        self,
        run_repository: RunRepository,
        task_queue: TaskQueuePort,
    ) -> None:
        self.run_repository = run_repository
        self.task_queue = task_queue

    def submit(self, payload: RunCreateInput, agent: PublishedAgent) -> RunRecord:
        effective_agent = _resolve_submission_agent(agent)
        provenance = agent.provenance.model_copy(deep=True) if agent.provenance else None
        if provenance is not None:
            provenance.eval_job_id = payload.eval_job_id
            provenance.dataset_sample_id = payload.dataset_sample_id
        spec = RunSpec(
            project=payload.project,
            dataset=payload.dataset,
            eval_job_id=payload.eval_job_id,
            dataset_sample_id=payload.dataset_sample_id,
            agent_id=payload.agent_id,
            model=effective_agent.default_model,
            entrypoint=effective_agent.entrypoint,
            agent_type=effective_agent.adapter_kind(),
            input_summary=payload.input_summary,
            prompt=payload.prompt,
            tags=list(payload.tags),
            project_metadata=dict(payload.project_metadata),
            provenance=provenance,
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
