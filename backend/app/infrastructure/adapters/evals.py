from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from app.core.errors import AgentNotPublishedError
from app.modules.agents.application.ports import RunnableAgentCatalogPort
from app.modules.datasets.domain.models import DatasetSample
from app.modules.evals.domain.models import EvalJobRecord, EvalRunState
from app.modules.runs.domain.models import RunRecord, RunSpec, TrajectoryStep
from app.modules.runs.domain.policies import RunAggregate
from app.modules.shared.application.ports import TaskQueuePort
from app.modules.shared.domain.enums import AdapterKind
from app.modules.shared.domain.tasks import QueuedTask, TaskType


class _RunRepository(Protocol):
    def list(self) -> Sequence[RunRecord]: ...

    def save(self, run: RunRecord) -> None: ...


class _TrajectoryRepository(Protocol):
    def list_for_run(self, run_id: str | UUID) -> Sequence[TrajectoryStep]: ...


def _merge_tags(primary: list[str], secondary: list[str]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for value in [*primary, *secondary]:
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def _adapter_kind_for_framework(framework: str) -> AdapterKind:
    normalized = framework.strip().lower()
    if normalized == AdapterKind.OPENAI_AGENTS.value:
        return AdapterKind.OPENAI_AGENTS
    if normalized == AdapterKind.LANGCHAIN.value:
        return AdapterKind.LANGCHAIN
    if normalized == AdapterKind.MCP.value:
        return AdapterKind.MCP
    raise ValueError(f"unsupported published agent framework '{framework}'")


class RunnableAgentLookupAdapter:
    def __init__(self, agent_catalog: RunnableAgentCatalogPort) -> None:
        self.agent_catalog = agent_catalog

    def exists(self, agent_id: str) -> bool:
        return self.agent_catalog.get_agent(agent_id) is not None


class StateEvalRunGateway:
    def __init__(
        self,
        run_repository: _RunRepository,
        trajectory_repository: _TrajectoryRepository,
        task_queue: TaskQueuePort,
        agent_catalog: RunnableAgentCatalogPort,
    ) -> None:
        self.run_repository = run_repository
        self.trajectory_repository = trajectory_repository
        self.task_queue = task_queue
        self.agent_catalog = agent_catalog

    def create_eval_run(self, job: EvalJobRecord, sample: DatasetSample) -> UUID:
        agent = self.agent_catalog.get_agent(job.agent_id)
        if agent is None:
            raise AgentNotPublishedError(job.agent_id)

        spec = RunSpec(
            project=job.project,
            dataset=job.dataset,
            agent_id=job.agent_id,
            model=agent.default_model,
            entrypoint=agent.entrypoint,
            agent_type=_adapter_kind_for_framework(agent.framework),
            input_summary=sample.input,
            prompt=sample.input,
            tags=_merge_tags(job.tags, sample.tags),
            project_metadata={
                "agent_snapshot": agent.to_snapshot(),
            },
            eval_job_id=job.eval_job_id,
            dataset_sample_id=sample.sample_id,
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
        return run.run_id

    def list_eval_runs(self, eval_job_id: str | UUID) -> list[EvalRunState]:
        resolved_eval_job_id = UUID(str(eval_job_id))
        runs = [
            run
            for run in self.run_repository.list()
            if run.eval_job_id == resolved_eval_job_id and run.dataset_sample_id is not None
        ]
        runs.sort(key=lambda run: run.created_at)

        states: list[EvalRunState] = []
        for run in runs:
            trajectory = self.trajectory_repository.list_for_run(run.run_id)
            actual = trajectory[-1].output if trajectory else None
            states.append(
                EvalRunState(
                    run_id=run.run_id,
                    dataset_sample_id=run.dataset_sample_id or "",
                    status=run.status,
                    actual=actual,
                    error_code=run.error_code,
                    error_message=run.error_message,
                    termination_reason=run.termination_reason,
                )
            )
        return states
