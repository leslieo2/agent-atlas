from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

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


class TraceRepository(Protocol):
    def append(self, span: TraceSpan) -> None: ...


class TrajectoryRepository(Protocol):
    def append(self, step: Any) -> None: ...


class TrajectoryStepProjectorPort(Protocol):
    def project(
        self,
        event: TraceIngestEvent,
        span: TraceSpan | None = None,
    ) -> Any: ...


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


class RunTracingStatePort(Protocol):
    def record_tracing(
        self,
        run_id: str | UUID,
        tracing: TracingMetadata,
    ) -> None: ...


@dataclass(frozen=True)
class RunTraceLookup:
    run_id: UUID
    created_at: datetime


class RunTraceLookupPort(Protocol):
    def get(self, run_id: str | UUID) -> RunTraceLookup | None: ...


__all__ = [
    "RunObservationSinkPort",
    "RunTraceLookup",
    "RunTraceLookupPort",
    "RunTracingStatePort",
    "TraceExportPort",
    "TraceIngestionPort",
    "TraceProjectorPort",
    "TraceQueryPort",
    "TraceRepository",
    "TrajectoryRepository",
    "TrajectoryStepProjectorPort",
]
