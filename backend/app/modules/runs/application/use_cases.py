from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from app.modules.runs.application.ports import (
    RunRepository,
    TrajectoryRepository,
)
from app.modules.runs.domain.models import RunRecord, RunSpec, TrajectoryStep
from app.modules.runs.domain.policies import RunAggregate
from app.modules.shared.application.ports import TaskQueuePort
from app.modules.shared.domain.enums import RunStatus
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
        model: str | None,
        tag: str | None,
        created_from: datetime | None,
        created_to: datetime | None,
    ) -> list[RunRecord]:
        def _to_utc_naive(value: datetime | None) -> datetime | None:
            if not value or value.tzinfo is None:
                return value
            return value.astimezone(UTC).replace(tzinfo=None)

        created_from = _to_utc_naive(created_from)
        created_to = _to_utc_naive(created_to)
        runs = self.run_repository.list()
        if status:
            runs = [run for run in runs if run.status == status]
        if project:
            runs = [run for run in runs if run.project == project]
        if dataset:
            runs = [run for run in runs if run.dataset == dataset]
        if model:
            runs = [run for run in runs if run.model == model]
        if tag:
            runs = [run for run in runs if tag in run.tags]
        if created_from:
            runs = [run for run in runs if run.created_at >= created_from]
        if created_to:
            runs = [run for run in runs if run.created_at <= created_to]
        return sorted(runs, key=lambda run: run.created_at, reverse=True)

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
    ) -> None:
        self.run_repository = run_repository
        self.task_queue = task_queue

    def create_run(self, payload: RunSpec) -> RunRecord:
        run = RunAggregate.create(payload)
        self.run_repository.save(run)
        self.task_queue.enqueue(
            QueuedTask(
                task_type=TaskType.RUN_EXECUTION,
                target_id=run.run_id,
                payload=payload.model_dump(mode="json"),
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
