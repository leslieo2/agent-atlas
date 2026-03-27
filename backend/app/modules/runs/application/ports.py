from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.modules.runs.application.results import PublishedRunExecutionResult
from app.modules.runs.domain.models import (
    RunRecord,
    RunSpec,
    TrajectoryStep,
)
from app.modules.traces.domain.models import TraceIngestEvent, TraceSpan


class RunRepository(Protocol):
    def get(self, run_id: str | UUID) -> RunRecord | None: ...

    def list(self) -> list[RunRecord]: ...

    def save(self, run: RunRecord) -> None: ...


class TrajectoryRepository(Protocol):
    def list_for_run(self, run_id: str | UUID) -> list[TrajectoryStep]: ...

    def append(self, step: TrajectoryStep) -> None: ...


class TrajectoryStepProjectorPort(Protocol):
    def project(
        self,
        event: TraceIngestEvent,
        span: TraceSpan | None = None,
    ) -> TrajectoryStep: ...


class PublishedRunRuntimePort(Protocol):
    def execute_published(
        self,
        run_id: UUID,
        payload: RunSpec,
    ) -> PublishedRunExecutionResult: ...


class TraceIngestionPort(Protocol):
    def ingest(self, event: TraceIngestEvent) -> TraceSpan: ...
