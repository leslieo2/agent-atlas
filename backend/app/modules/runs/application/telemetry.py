from __future__ import annotations

from uuid import UUID

from app.modules.runs.application.ports import (
    RunRepository,
    TrajectoryRepository,
    TrajectoryStepProjectorPort,
)
from app.modules.runs.domain.models import TrajectoryStep
from app.modules.runs.domain.policies import RunAggregate
from app.modules.shared.domain.models import ObservabilityMetadata
from app.modules.traces.application.ports import TraceExporterPort, TraceProjectorPort
from app.modules.traces.domain.models import TraceIngestEvent, TraceSpan


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
        trace_projector: TraceProjectorPort,
        trace_exporter: TraceExporterPort,
        trajectory_recorder: TrajectoryRecorder,
    ) -> None:
        self.run_repository = run_repository
        self.trace_projector = trace_projector
        self.trace_exporter = trace_exporter
        self.trajectory_recorder = trajectory_recorder

    def ingest(self, event: TraceIngestEvent) -> TraceSpan:
        span = self.trace_projector.project(event)
        self.trajectory_recorder.record(event=event, span=span)
        observability = self.trace_exporter.export([event], [span])
        if observability is not None:
            self._record_observability(event.run_id, observability)
        return span

    def ingest_many(self, events: list[TraceIngestEvent]) -> list[TraceSpan]:
        spans = [self.trace_projector.project(event) for event in events]
        for event, span in zip(events, spans, strict=True):
            self.trajectory_recorder.record(event=event, span=span)
        observability = self.trace_exporter.export(events, spans)
        if observability is not None and events:
            self._record_observability(events[0].run_id, observability)
        return spans

    def _record_observability(
        self,
        run_id: str | UUID,
        observability: ObservabilityMetadata,
    ) -> None:
        run = self.run_repository.get(run_id)
        if not run:
            return
        updated = RunAggregate.load(run)
        updated.run.observability = observability
        if updated.run.provenance is not None:
            updated.run.provenance.trace_backend = observability.backend
        self.run_repository.save(updated.run)
