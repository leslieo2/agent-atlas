from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from app.modules.runs.domain.models import RunRecord, TrajectoryStep
from app.modules.shared.domain.models import TracingMetadata
from app.modules.shared.domain.traces import TraceIngestEvent, TraceSpan


class TraceQueryPort(Protocol):
    def list_for_run(self, run_id: str | UUID) -> list[TraceSpan]: ...

    def backend_name(self) -> str: ...


class TraceExportPort(Protocol):
    def export(
        self,
        events: list[TraceIngestEvent],
        spans: list[TraceSpan],
    ) -> TracingMetadata | None: ...


class RunRepository(Protocol):
    def get(self, run_id: str | UUID) -> RunRecord | None: ...

    def list(self) -> list[RunRecord]: ...

    def save(self, run: RunRecord) -> None: ...


class TrajectoryRepository(Protocol):
    def list_for_run(self, run_id: str | UUID) -> list[TrajectoryStep]: ...

    def append(self, step: TrajectoryStep) -> None: ...


class TraceRepository(Protocol):
    def list_for_run(self, run_id: str | UUID) -> list[TraceSpan]: ...

    def append(self, span: TraceSpan) -> None: ...


class TrajectoryStepProjectorPort(Protocol):
    def project(
        self,
        event: TraceIngestEvent,
        span: TraceSpan | None = None,
    ) -> TrajectoryStep: ...


class TraceProjectorPort(Protocol):
    def project(self, event: TraceIngestEvent) -> TraceSpan: ...

    def normalize(
        self,
        span: TraceSpan,
        event: TraceIngestEvent | None = None,
    ) -> dict[str, object]: ...


class TraceIngestionPort(Protocol):
    def ingest(self, event: TraceIngestEvent) -> TraceSpan: ...


class RunObservationSinkPort(Protocol):
    def ingest(self, event: TraceIngestEvent) -> TraceSpan: ...

    def ingest_many(self, events: list[TraceIngestEvent]) -> list[TraceSpan]: ...


@dataclass(frozen=True)
class RunTraceLookup:
    run_id: UUID
    created_at: datetime


class RunTraceLookupPort(Protocol):
    def get(self, run_id: str | UUID) -> RunTraceLookup | None: ...


__all__ = [
    "RunObservationSinkPort",
    "RunRepository",
    "RunTraceLookup",
    "RunTraceLookupPort",
    "TraceExportPort",
    "TraceIngestionPort",
    "TraceProjectorPort",
    "TraceQueryPort",
    "TraceRepository",
    "TrajectoryRepository",
    "TrajectoryStepProjectorPort",
]
