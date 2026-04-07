from collections.abc import Sequence

from agent_atlas_contracts.runtime import (
    TraceIngestEvent as ContractTraceIngestEvent,
)
from agent_atlas_contracts.runtime import (
    empty_artifact_manifest,
    event_envelope_to_trace_event,
    event_envelopes_to_trace_events,
    producer_for_runtime,
    terminal_result_from_runtime_result,
    trace_event_to_event_envelope,
)

from app.modules.shared.domain.traces import TraceIngestEvent


def runtime_trace_event_to_domain(event: ContractTraceIngestEvent) -> TraceIngestEvent:
    return TraceIngestEvent.model_validate(event.model_dump(mode="json"))


def runtime_trace_events_to_domain(
    events: Sequence[ContractTraceIngestEvent],
) -> list[TraceIngestEvent]:
    return [runtime_trace_event_to_domain(event) for event in events]


__all__ = [
    "empty_artifact_manifest",
    "event_envelope_to_trace_event",
    "event_envelopes_to_trace_events",
    "producer_for_runtime",
    "runtime_trace_event_to_domain",
    "runtime_trace_events_to_domain",
    "terminal_result_from_runtime_result",
    "trace_event_to_event_envelope",
]
