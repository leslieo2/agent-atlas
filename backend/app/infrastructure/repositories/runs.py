from __future__ import annotations

from uuid import UUID

from app.infrastructure.repositories.common import state, to_uuid
from app.modules.runs.domain.models import RunRecord, TrajectoryStep
from app.modules.traces.domain.models import TraceSpan


class StateRunRepository:
    def get(self, run_id: str | UUID) -> RunRecord | None:
        with state.lock:
            return state.runs.get(to_uuid(run_id))

    def list(self) -> list[RunRecord]:
        with state.lock:
            return list(state.runs.values())

    def save(self, run: RunRecord) -> None:
        state.save_run(run)


class StateTrajectoryRepository:
    def list_for_run(self, run_id: str | UUID) -> list[TrajectoryStep]:
        return state.copy_trajectory(to_uuid(run_id))

    def append(self, step: TrajectoryStep) -> None:
        state.append_trajectory_step(step)


class StateTraceRepository:
    def list_for_run(self, run_id: str | UUID) -> list[TraceSpan]:
        return state.copy_trace_spans(to_uuid(run_id))

    def append(self, span: TraceSpan) -> None:
        state.append_trace_span(span)


__all__ = [
    "StateRunRepository",
    "StateTraceRepository",
    "StateTrajectoryRepository",
]
