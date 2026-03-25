from __future__ import annotations

from app.modules.traces.application.ports import TraceProjectorPort, TraceRepository
from app.modules.traces.domain.models import TraceIngestEvent, TraceSpan


class TraceRecorder:
    def __init__(self, trace_repository: TraceRepository) -> None:
        self.trace_repository = trace_repository

    def record(self, span: TraceSpan) -> TraceSpan:
        self.trace_repository.append(span)
        return span


class TraceIngestionWorkflow:
    def __init__(
        self,
        trace_projector: TraceProjectorPort,
        trace_recorder: TraceRecorder,
    ) -> None:
        self.trace_projector = trace_projector
        self.trace_recorder = trace_recorder

    def ingest(self, event: TraceIngestEvent) -> TraceSpan:
        span = self.trace_projector.project(event)
        return self.trace_recorder.record(span)

    def normalize(self, event: TraceIngestEvent) -> dict[str, object]:
        span = self.ingest(event)
        return self.trace_projector.normalize(span)


class TraceCommands:
    def __init__(self, workflow: TraceIngestionWorkflow) -> None:
        self.workflow = workflow

    def ingest(self, event: TraceIngestEvent) -> TraceSpan:
        return self.workflow.ingest(event)

    def normalize(self, event: TraceIngestEvent) -> dict[str, object]:
        return self.workflow.normalize(event)
