from __future__ import annotations

from uuid import UUID

from app.db.persistence import StatePersistence
from app.infrastructure.repositories.common import resolve_state_persistence, to_uuid
from app.modules.runs.domain.models import RunRecord
from app.modules.shared.domain.models import TrajectoryStepRecord
from app.modules.shared.domain.traces import TraceSpan


class StateRunRepository:
    def __init__(self, persistence: StatePersistence | None = None) -> None:
        self._persistence = resolve_state_persistence(persistence)

    def get(self, run_id: str | UUID) -> RunRecord | None:
        return self._persistence.get_run(to_uuid(run_id))

    def list(self) -> list[RunRecord]:
        return self._persistence.list_runs()

    def save(self, run: RunRecord) -> None:
        self._persistence.save_run(run)


class StateTrajectoryRepository:
    def __init__(self, persistence: StatePersistence | None = None) -> None:
        self._persistence = resolve_state_persistence(persistence)

    def list_for_run(self, run_id: str | UUID) -> list[TrajectoryStepRecord]:
        return self._persistence.list_trajectory(to_uuid(run_id))

    def append(self, step: TrajectoryStepRecord) -> None:
        self._persistence.append_trajectory_step(step)


class StateTraceRepository:
    def __init__(self, persistence: StatePersistence | None = None) -> None:
        self._persistence = resolve_state_persistence(persistence)

    def list_for_run(self, run_id: str | UUID) -> list[TraceSpan]:
        return self._persistence.list_trace_spans(to_uuid(run_id))

    def append(self, span: TraceSpan) -> None:
        self._persistence.append_trace_span(span)


__all__ = [
    "StateRunRepository",
    "StateTraceRepository",
    "StateTrajectoryRepository",
]
