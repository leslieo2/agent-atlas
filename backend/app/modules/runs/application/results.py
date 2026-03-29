from __future__ import annotations

from dataclasses import dataclass, field

from app.modules.runs.domain.models import RuntimeExecutionResult
from app.modules.traces.domain.models import TraceIngestEvent


@dataclass(frozen=True)
class PublishedRunExecutionResult:
    runtime_result: RuntimeExecutionResult
    trace_events: list[TraceIngestEvent] = field(default_factory=list)


@dataclass(frozen=True)
class RunnerExecutionResult:
    runner_backend: str
    artifact_ref: str | None
    image_ref: str | None
    execution: PublishedRunExecutionResult
