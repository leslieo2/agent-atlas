from __future__ import annotations

from agent_atlas_contracts.runtime import TraceIngestEvent

from app.modules.shared.domain.observability import TracingMetadata
from app.modules.shared.domain.traces import TraceSpan


class NoopTraceExporter:
    def export(
        self,
        events: list[TraceIngestEvent],
        spans: list[TraceSpan],
    ) -> TracingMetadata | None:
        return None


__all__ = ["NoopTraceExporter"]
