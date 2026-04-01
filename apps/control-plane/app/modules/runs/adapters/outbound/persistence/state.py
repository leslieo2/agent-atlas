from __future__ import annotations

from typing import cast
from uuid import UUID

from app.db.persistence import StatePersistence
from app.infrastructure.repositories.common import persistence, to_uuid
from app.modules.runs.domain.models import RunRecord
from app.modules.shared.domain.models import TrajectoryStepRecord
from app.modules.shared.domain.traces import TraceSpan

state_persistence = cast(StatePersistence, persistence)


class StateRunRepository:
    def get(self, run_id: str | UUID) -> RunRecord | None:
        return state_persistence.get_run(to_uuid(run_id))

    def list(self) -> list[RunRecord]:
        return state_persistence.list_runs()

    def save(self, run: RunRecord) -> None:
        state_persistence.save_run(run)


class StateTrajectoryRepository:
    def list_for_run(self, run_id: str | UUID) -> list[TrajectoryStepRecord]:
        return state_persistence.list_trajectory(to_uuid(run_id))

    def append(self, step: TrajectoryStepRecord) -> None:
        state_persistence.append_trajectory_step(step)


class StateTraceRepository:
    def list_for_run(self, run_id: str | UUID) -> list[TraceSpan]:
        return state_persistence.list_trace_spans(to_uuid(run_id))

    def append(self, span: TraceSpan) -> None:
        state_persistence.append_trace_span(span)


__all__ = [
    "StateRunRepository",
    "StateTraceRepository",
    "StateTrajectoryRepository",
]
