from __future__ import annotations

from uuid import UUID

from app.infrastructure.repositories.common import persistence, to_uuid
from app.modules.runs.domain.models import RunRecord, TrajectoryStep
from app.modules.traces.domain.models import TraceSpan


class StateRunRepository:
    def get(self, run_id: str | UUID) -> RunRecord | None:
        return persistence.get_run(to_uuid(run_id))

    def list(self) -> list[RunRecord]:
        return persistence.list_runs()

    def save(self, run: RunRecord) -> None:
        persistence.save_run(run)


class StateTrajectoryRepository:
    def list_for_run(self, run_id: str | UUID) -> list[TrajectoryStep]:
        return persistence.list_trajectory(to_uuid(run_id))

    def append(self, step: TrajectoryStep) -> None:
        persistence.append_trajectory_step(step)


class StateTraceRepository:
    def list_for_run(self, run_id: str | UUID) -> list[TraceSpan]:
        return persistence.list_trace_spans(to_uuid(run_id))

    def append(self, span: TraceSpan) -> None:
        persistence.append_trace_span(span)


__all__ = [
    "StateRunRepository",
    "StateTraceRepository",
    "StateTrajectoryRepository",
]
