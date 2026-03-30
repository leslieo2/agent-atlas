from __future__ import annotations

from dataclasses import dataclass, field

from agent_atlas_contracts.execution import ArtifactManifest, EventEnvelope, TerminalResult

from app.modules.runs.application.runtime_translation import event_envelopes_to_trace_events
from app.modules.runs.domain.models import RuntimeExecutionResult
from app.modules.shared.domain.traces import TraceIngestEvent


@dataclass(frozen=True)
class PublishedRunExecutionResult:
    runtime_result: RuntimeExecutionResult
    event_envelopes: list[EventEnvelope] = field(default_factory=list)
    terminal_result: TerminalResult | None = None
    artifact_manifest: ArtifactManifest | None = None
    trace_events: list[TraceIngestEvent] = field(default_factory=list)

    def projected_trace_events(self) -> list[TraceIngestEvent]:
        if self.trace_events:
            return list(self.trace_events)
        return event_envelopes_to_trace_events(self.event_envelopes)


@dataclass(frozen=True)
class RunnerExecutionResult:
    runner_backend: str
    artifact_ref: str | None
    image_ref: str | None
    execution: PublishedRunExecutionResult
