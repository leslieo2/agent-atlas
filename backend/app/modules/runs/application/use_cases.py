from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from app.core.errors import AgentNotPublishedError
from app.modules.agents.application.ports import RunnableAgentCatalogPort
from app.modules.execution.application.ports import ExecutionControlPort
from app.modules.execution.domain.models import CancelRequest
from app.modules.runs.application.ports import (
    RunRepository,
    TrajectoryRepository,
)
from app.modules.runs.application.services import RunSubmissionService
from app.modules.runs.domain.models import RunCreateInput, RunRecord, TrajectoryStep
from app.modules.shared.domain.enums import RunStatus
from app.modules.traces.application.ports import TraceBackendPort
from app.modules.traces.domain.models import TraceSpan


class RunQueries:
    def __init__(
        self,
        run_repository: RunRepository,
        trajectory_repository: TrajectoryRepository,
        trace_backend: TraceBackendPort,
    ) -> None:
        self.run_repository = run_repository
        self.trajectory_repository = trajectory_repository
        self.trace_backend = trace_backend

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
        return self.trace_backend.list_for_run(run_id)


class RunCommands:
    def __init__(
        self,
        run_repository: RunRepository,
        agent_catalog: RunnableAgentCatalogPort,
        submission_service: RunSubmissionService,
        execution_control: ExecutionControlPort,
    ) -> None:
        self.run_repository = run_repository
        self.agent_catalog = agent_catalog
        self.submission_service = submission_service
        self.execution_control = execution_control

    def create_run(self, payload: RunCreateInput) -> RunRecord:
        agent = self.agent_catalog.get_agent(payload.agent_id)
        if agent is None:
            raise AgentNotPublishedError(payload.agent_id)

        return self.submission_service.submit(payload, agent)

    def terminate(self, run_id: str | UUID, reason: str = "cancelled by user") -> RunRecord | None:
        run = self.run_repository.get(run_id)
        if not run:
            return None
        if not self.execution_control.cancel_run(
            CancelRequest(run_id=run.run_id, attempt_id=run.attempt_id, reason=reason)
        ):
            return None
        return self.run_repository.get(run_id)
