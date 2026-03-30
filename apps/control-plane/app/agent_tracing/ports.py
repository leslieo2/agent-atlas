from __future__ import annotations

from typing import Protocol
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


class TraceLinkResolverPort(Protocol):
    def build_trace_url(self, trace_id: str | None) -> str | None: ...

    def build_project_url(
        self,
        *,
        experiment_id: str | UUID | None = None,
        run_id: str | UUID | None = None,
    ) -> str | None: ...
