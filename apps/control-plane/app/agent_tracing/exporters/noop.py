from __future__ import annotations

from app.modules.shared.domain.models import TracingMetadata
from app.modules.shared.domain.traces import TraceIngestEvent, TraceSpan


class NoopTraceExporter:
    def export(
        self,
        events: list[TraceIngestEvent],
        spans: list[TraceSpan],
    ) -> TracingMetadata | None:
        return None


__all__ = ["NoopTraceExporter"]
