from __future__ import annotations

from app.modules.traces.application.ports import (
    TraceProjectorPort,
)
from app.modules.traces.domain.models import TraceIngestEvent, TraceSpan


class TraceIngestionWorkflow:
    def __init__(
        self,
        trace_projector: TraceProjectorPort,
    ) -> None:
        self.trace_projector = trace_projector

    def ingest(self, event: TraceIngestEvent) -> TraceSpan:
        return self.trace_projector.project(event)

    def normalize(self, event: TraceIngestEvent) -> dict[str, object]:
        span = self.ingest(event)
        return self.trace_projector.normalize(span, event)


class TraceCommands:
    def __init__(self, workflow: TraceIngestionWorkflow) -> None:
        self.workflow = workflow

    def ingest(self, event: TraceIngestEvent) -> TraceSpan:
        return self.workflow.ingest(event)

    def normalize(self, event: TraceIngestEvent) -> dict[str, object]:
        return self.workflow.normalize(event)
