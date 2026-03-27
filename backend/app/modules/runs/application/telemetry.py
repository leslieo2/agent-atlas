from __future__ import annotations

from app.modules.runs.application.ports import (
    TraceIngestionPort,
    TrajectoryRepository,
    TrajectoryStepProjectorPort,
)
from app.modules.runs.domain.models import TrajectoryStep
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
        trace_ingestor: TraceIngestionPort,
        trajectory_recorder: TrajectoryRecorder,
    ) -> None:
        self.trace_ingestor = trace_ingestor
        self.trajectory_recorder = trajectory_recorder

    def ingest(self, event: TraceIngestEvent) -> TraceSpan:
        span = self.trace_ingestor.ingest(event)
        self.trajectory_recorder.record(event=event, span=span)
        return span
