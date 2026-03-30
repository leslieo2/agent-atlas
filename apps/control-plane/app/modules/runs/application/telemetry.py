from __future__ import annotations

from uuid import UUID

from app.modules.runs.application.ports import (
    RunRepository,
    TraceExporterPort,
    TraceProjectorPort,
    TraceRepository,
    TrajectoryRepository,
    TrajectoryStepProjectorPort,
)
from app.modules.runs.domain.models import TrajectoryStep
from app.modules.runs.domain.policies import RunAggregate
from app.modules.shared.domain.models import TracePointer, TracingMetadata
from app.modules.shared.domain.traces import TraceIngestEvent, TraceSpan


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
    ) -> TrajectoryStep:
        step = self.step_projector.project(event=event, span=span)
        self.trajectory_repository.append(step)
        return step


class RunTelemetryIngestionService:
    def __init__(
        self,
        run_repository: RunRepository,
        trace_repository: TraceRepository,
        trace_projector: TraceProjectorPort,
        trace_exporter: TraceExporterPort,
        trajectory_recorder: TrajectoryRecorder,
    ) -> None:
        self.run_repository = run_repository
        self.trace_repository = trace_repository
        self.trace_projector = trace_projector
        self.trace_exporter = trace_exporter
        self.trajectory_recorder = trajectory_recorder

    def ingest(self, event: TraceIngestEvent) -> TraceSpan:
        span = self.trace_projector.project(event)
        self.trace_repository.append(span)
        self.trajectory_recorder.record(event=event, span=span)
        tracing = self.trace_exporter.export([event], [span])
        if tracing is not None:
            self._record_tracing(event.run_id, tracing)
        return span

    def ingest_many(self, events: list[TraceIngestEvent]) -> list[TraceSpan]:
        spans = [self.trace_projector.project(event) for event in events]
        for event, span in zip(events, spans, strict=True):
            self.trace_repository.append(span)
            self.trajectory_recorder.record(event=event, span=span)
        tracing = self.trace_exporter.export(events, spans)
        if tracing is not None and events:
            self._record_tracing(events[0].run_id, tracing)
        return spans

    def _record_tracing(
        self,
        run_id: str | UUID,
        tracing: TracingMetadata,
    ) -> None:
        run = self.run_repository.get(run_id)
        if not run:
            return
        updated = RunAggregate.load(run)
        updated.run.tracing = tracing
        updated.run.trace_pointer = TracePointer(
            backend=tracing.backend,
            trace_id=tracing.trace_id,
            trace_url=tracing.trace_url,
            project_url=tracing.project_url,
        )
        if updated.run.provenance is not None:
            updated.run.provenance.trace_backend = tracing.backend
        self.run_repository.save(updated.run)
