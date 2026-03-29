from __future__ import annotations

from typing import Any, Protocol
from uuid import UUID

from app.modules.traces.domain.models import TraceIngestEvent, TraceSpan


class TraceBackendPort(Protocol):
    def list_for_run(self, run_id: str | UUID) -> list[TraceSpan]: ...

    def append(self, span: TraceSpan) -> None: ...

    def backend_name(self) -> str: ...


class TraceProjectorPort(Protocol):
    def project(self, event: TraceIngestEvent) -> TraceSpan: ...

    def normalize(
        self,
        span: TraceSpan,
        event: TraceIngestEvent | None = None,
    ) -> dict[str, Any]: ...


__all__ = ["TraceBackendPort", "TraceProjectorPort"]
