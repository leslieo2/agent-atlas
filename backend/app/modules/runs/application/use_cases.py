from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from app.core.errors import AgentNotPublishedError
from app.modules.agents.application.ports import RunnableAgentCatalogPort
from app.modules.runs.application.ports import (
    RunRepository,
    TrajectoryRepository,
)
from app.modules.runs.domain.models import RunCreateInput, RunRecord, RunSpec, TrajectoryStep
from app.modules.runs.domain.policies import RunAggregate
from app.modules.shared.application.ports import TaskQueuePort
from app.modules.shared.domain.enums import AdapterKind, RunStatus
from app.modules.shared.domain.tasks import QueuedTask, TaskType
from app.modules.traces.application.ports import TraceRepository
from app.modules.traces.domain.models import TraceSpan


class RunQueries:
    def __init__(
        self,
        run_repository: RunRepository,
        trajectory_repository: TrajectoryRepository,
        trace_repository: TraceRepository,
    ) -> None:
        self.run_repository = run_repository
        self.trajectory_repository = trajectory_repository
        self.trace_repository = trace_repository

    def list_runs(
        self,
        status: RunStatus | None,
        project: str | None,
        dataset: str | None,
        agent_id: str | None,
        model: str | None,
        tag: str | None,
        created_from: datetime | None,
        created_to: datetime | None,
    ) -> list[RunRecord]:
        def _to_utc_aware_optional(value: datetime | None) -> datetime | None:
            if value is None:
                return None
            if value.tzinfo is None:
                return value.replace(tzinfo=UTC)
            return value.astimezone(UTC)

        def _to_utc_aware(value: datetime) -> datetime:
            if value.tzinfo is None:
                return value.replace(tzinfo=UTC)
            return value.astimezone(UTC)

        created_from = _to_utc_aware_optional(created_from)
        created_to = _to_utc_aware_optional(created_to)
        runs = self.run_repository.list()
        if status:
            runs = [run for run in runs if run.status == status]
        if project:
            runs = [run for run in runs if run.project == project]
        if dataset:
            runs = [run for run in runs if run.dataset == dataset]
        if agent_id:
            runs = [run for run in runs if run.agent_id == agent_id]
        if model:
            runs = [run for run in runs if run.model == model]
        if tag:
            runs = [run for run in runs if tag in run.tags]
        if created_from:
            runs = [run for run in runs if _to_utc_aware(run.created_at) >= created_from]
        if created_to:
            runs = [run for run in runs if _to_utc_aware(run.created_at) <= created_to]
        return sorted(runs, key=lambda run: _to_utc_aware(run.created_at), reverse=True)

    def get_run(self, run_id: str | UUID) -> RunRecord | None:
        return self.run_repository.get(run_id)

    def get_trajectory(self, run_id: str | UUID) -> list[TrajectoryStep]:
        return self.trajectory_repository.list_for_run(run_id)

    def get_traces(self, run_id: str | UUID) -> list[TraceSpan]:
        return self.trace_repository.list_for_run(run_id)


class RunCommands:
    def __init__(
        self,
        run_repository: RunRepository,
        task_queue: TaskQueuePort,
        agent_catalog: RunnableAgentCatalogPort,
    ) -> None:
        self.run_repository = run_repository
        self.task_queue = task_queue
        self.agent_catalog = agent_catalog

    def create_run(self, payload: RunCreateInput) -> RunRecord:
        agent = self.agent_catalog.get_agent(payload.agent_id)
        if agent is None:
            raise AgentNotPublishedError(payload.agent_id)

        spec = RunSpec(
            project=payload.project,
            dataset=payload.dataset,
            agent_id=payload.agent_id,
            model=agent.default_model,
            entrypoint=agent.entrypoint,
            agent_type=AdapterKind.OPENAI_AGENTS,
            input_summary=payload.input_summary,
            prompt=payload.prompt,
            tags=payload.tags,
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

    def terminate(self, run_id: str | UUID, reason: str = "terminated by user") -> RunRecord | None:
        run = self.run_repository.get(run_id)
        if not run:
            return None
        try:
            updated = RunAggregate.load(run).terminate(reason)
        except ValueError:
            return None
        self.run_repository.save(updated)
        return updated
