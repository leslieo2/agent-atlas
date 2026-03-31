from __future__ import annotations

from uuid import UUID

from app.agent_tracing.contracts import (
    RunObservationSinkPort,
    RunTracingStatePort,
    TraceExportPort,
    TraceProjectorPort,
    TraceRepository,
    TrajectoryRepository,
    TrajectoryStepProjectorPort,
)
from app.modules.shared.domain.models import TracingMetadata, TrajectoryStepRecord
from app.modules.shared.domain.traces import TraceIngestEvent, TraceSpan


class TraceSpanRecorder:
    def __init__(
        self,
        trace_repository: TraceRepository,
        trace_projector: TraceProjectorPort,
    ) -> None:
        self.trace_repository = trace_repository
        self.trace_projector = trace_projector

    def record(self, event: TraceIngestEvent) -> TraceSpan:
        span = self.trace_projector.project(event)
        self.trace_repository.append(span)
        return span

    def record_many(self, events: list[TraceIngestEvent]) -> list[TraceSpan]:
        spans = [self.trace_projector.project(event) for event in events]
        for span in spans:
            self.trace_repository.append(span)
        return spans


class TrajectoryRecorder:
    def __init__(
        self,
        trajectory_repository: TrajectoryRepository,
        step_projector: TrajectoryStepProjectorPort,
    ) -> None:
        self.trajectory_repository = trajectory_repository
        self.step_projector = step_projector

    def record(
        self,
        event: TraceIngestEvent,
        span: TraceSpan | None = None,
    ) -> TrajectoryStepRecord:
        step = self.step_projector.project(event=event, span=span)
        self.trajectory_repository.append(step)
        return step

    def record_many(
        self,
        events: list[TraceIngestEvent],
        spans: list[TraceSpan],
    ) -> list[TrajectoryStepRecord]:
        return [
            self.record(event=event, span=span) for event, span in zip(events, spans, strict=True)
        ]


class RunTraceMetadataRecorder:
    def __init__(self, run_tracing_state: RunTracingStatePort) -> None:
        self.run_tracing_state = run_tracing_state

    def record(
        self,
        run_id: str | UUID,
        tracing: TracingMetadata,
    ) -> None:
        self.run_tracing_state.record_tracing(run_id, tracing)


class TraceExportCoordinator:
    def __init__(
        self,
        trace_exporter: TraceExportPort,
        trace_metadata_recorder: RunTraceMetadataRecorder,
    ) -> None:
        self.trace_exporter = trace_exporter
        self.trace_metadata_recorder = trace_metadata_recorder

    def export(
        self,
        *,
        run_id: str | UUID,
        events: list[TraceIngestEvent],
        spans: list[TraceSpan],
    ) -> TracingMetadata | None:
        tracing = self.trace_exporter.export(events, spans)
        if tracing is not None:
            self.trace_metadata_recorder.record(run_id, tracing)
        return tracing


class RunObservationService(RunObservationSinkPort):
    def __init__(
        self,
        trace_span_recorder: TraceSpanRecorder,
        trajectory_recorder: TrajectoryRecorder,
        trace_export_coordinator: TraceExportCoordinator,
    ) -> None:
        self.trace_span_recorder = trace_span_recorder
        self.trajectory_recorder = trajectory_recorder
        self.trace_export_coordinator = trace_export_coordinator

    def ingest(self, event: TraceIngestEvent) -> TraceSpan:
        span = self.trace_span_recorder.record(event)
        self.trajectory_recorder.record(event=event, span=span)
        self.trace_export_coordinator.export(
            run_id=event.run_id,
            events=[event],
            spans=[span],
        )
        return span

    def ingest_many(self, events: list[TraceIngestEvent]) -> list[TraceSpan]:
        if not events:
            return []
        spans = self.trace_span_recorder.record_many(events)
        self.trajectory_recorder.record_many(events, spans)
        self.trace_export_coordinator.export(
            run_id=events[0].run_id,
            events=events,
            spans=spans,
        )
        return spans


RunTelemetryIngestionService = RunObservationService


__all__ = [
    "RunObservationService",
    "RunTelemetryIngestionService",
    "RunTraceMetadataRecorder",
    "TraceExportCoordinator",
    "TraceSpanRecorder",
    "TrajectoryRecorder",
]
