from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.modules.runs.domain.models import RunRecord
from app.modules.shared.application.contracts import (
    TraceRepository as SharedTraceRepository,
)
from app.modules.shared.application.contracts import (
    TrajectoryRepository as SharedTrajectoryRepository,
)
from app.modules.shared.domain.observability import TrajectoryStepRecord
from app.modules.shared.domain.traces import TraceSpan


class RunRepository(Protocol):
    def get(self, run_id: str | UUID) -> RunRecord | None: ...

    def list(self) -> list[RunRecord]: ...

    def save(self, run: RunRecord) -> None: ...


class TraceRepository(SharedTraceRepository, Protocol):
    def list_for_run(self, run_id: str | UUID) -> list[TraceSpan]: ...


class TrajectoryRepository(SharedTrajectoryRepository, Protocol):
    def append(self, step: TrajectoryStepRecord) -> None: ...
