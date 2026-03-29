from __future__ import annotations

from typing import Any, Protocol
from uuid import UUID

from app.modules.shared.domain.models import ObservabilityMetadata
from app.modules.traces.domain.models import TraceIngestEvent, TraceSpan


class TraceBackendPort(Protocol):
    def list_for_run(self, run_id: str | UUID) -> list[TraceSpan]: ...

    def backend_name(self) -> str: ...


class TraceExporterPort(Protocol):
    def export(
        self,
        events: list[TraceIngestEvent],
        spans: list[TraceSpan],
    ) -> ObservabilityMetadata | None: ...


class TraceProjectorPort(Protocol):
    def project(self, event: TraceIngestEvent) -> TraceSpan: ...

    def normalize(
        self,
        span: TraceSpan,
        event: TraceIngestEvent | None = None,
    ) -> dict[str, Any]: ...


__all__ = ["TraceBackendPort", "TraceExporterPort", "TraceProjectorPort"]
