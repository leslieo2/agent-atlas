from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from pydantic import ValidationError

from app.execution_plane.contracts import (
    ArtifactManifest,
    EventEnvelope,
    ProducerInfo,
    RunnerRunSpec,
    TerminalMetrics,
    TerminalResult,
)
from app.modules.runs.domain.models import RuntimeExecutionResult
from app.modules.shared.domain.enums import StepType
from app.modules.shared.domain.models import TraceTelemetryMetadata
from app.modules.traces.domain.models import TraceIngestEvent


def producer_for_runtime(
    *,
    runtime: str,
    framework: str | None = None,
    language: str = "python",
    version: str | None = None,
) -> ProducerInfo:
    return ProducerInfo(
        kind="runner",
        runtime=runtime,
        framework=framework or runtime,
        language=language,
        version=version,
    )


def trace_event_to_event_envelope(
    event: TraceIngestEvent,
    *,
    experiment_id,
    attempt: int,
    attempt_id,
    producer: ProducerInfo,
    sequence: int,
) -> EventEnvelope:
    success = event.output.get("success")
    if event.step_type == StepType.TOOL:
        event_type = "tool.failed" if success is False else "tool.succeeded"
    else:
        event_type = "llm.response"

    payload: dict[str, Any] = {
        "step_type": event.step_type.value,
        "name": event.name,
        "input": dict(event.input),
        "output": dict(event.output),
        "tool_name": event.tool_name,
        "latency_ms": event.latency_ms,
        "token_usage": event.token_usage,
        "image_digest": event.image_digest,
        "prompt_version": event.prompt_version,
    }
    if event.metadata is not None:
        payload["metadata"] = event.metadata.model_dump(mode="json")

    return EventEnvelope(
        run_id=event.run_id,
        experiment_id=experiment_id,
        attempt=attempt,
        attempt_id=attempt_id,
        event_id=event.span_id,
        parent_event_id=event.parent_span_id,
        sequence=sequence,
        event_type=event_type,
        producer=producer,
        payload=payload,
    )


def event_envelope_to_trace_event(event: EventEnvelope) -> TraceIngestEvent | None:
    payload = event.payload
    raw_step_type = payload.get("step_type")
    try:
        step_type = (
            StepType(raw_step_type)
            if isinstance(raw_step_type, str)
            else _step_type_from_event_type(event.event_type)
        )
    except ValueError:
        return None

    name = payload.get("name")
    input_payload = payload.get("input")
    output_payload = payload.get("output")
    if (
        not isinstance(name, str)
        or not isinstance(input_payload, dict)
        or not isinstance(output_payload, dict)
    ):
        return None

    metadata = _metadata_from_payload(payload.get("metadata"))
    tool_name = payload.get("tool_name")
    return TraceIngestEvent(
        run_id=event.run_id,
        span_id=event.event_id,
        parent_span_id=event.parent_event_id,
        step_type=step_type,
        name=name,
        input=input_payload,
        output=output_payload,
        tool_name=tool_name if isinstance(tool_name, str) else None,
        latency_ms=_int_payload_value(payload.get("latency_ms")),
        token_usage=_int_payload_value(payload.get("token_usage")),
        image_digest=_string_payload_value(payload.get("image_digest")),
        prompt_version=_string_payload_value(payload.get("prompt_version")),
        metadata=metadata,
    )


def event_envelopes_to_trace_events(events: Iterable[EventEnvelope]) -> list[TraceIngestEvent]:
    trace_events: list[TraceIngestEvent] = []
    for event in events:
        trace_event = event_envelope_to_trace_event(event)
        if trace_event is not None:
            trace_events.append(trace_event)
    return trace_events


def terminal_result_from_runtime_result(
    *,
    payload: RunnerRunSpec,
    runtime_result: RuntimeExecutionResult,
    producer: ProducerInfo,
    tool_calls: int,
) -> TerminalResult:
    return TerminalResult(
        run_id=payload.run_id,
        experiment_id=payload.experiment_id,
        attempt=payload.attempt,
        attempt_id=payload.attempt_id,
        status="succeeded",
        output=runtime_result.output,
        producer=producer,
        metrics=TerminalMetrics(
            latency_ms=runtime_result.latency_ms,
            token_usage=runtime_result.token_usage,
            tool_calls=tool_calls,
        ),
    )


def empty_artifact_manifest(
    *,
    payload: RunnerRunSpec,
    producer: ProducerInfo,
) -> ArtifactManifest:
    return ArtifactManifest(
        run_id=payload.run_id,
        experiment_id=payload.experiment_id,
        attempt=payload.attempt,
        attempt_id=payload.attempt_id,
        producer=producer,
        artifacts=[],
    )


def _step_type_from_event_type(event_type: str) -> StepType:
    if event_type.startswith("tool."):
        return StepType.TOOL
    return StepType.LLM


def _int_payload_value(value: object) -> int:
    return value if isinstance(value, int) else 0


def _string_payload_value(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _metadata_from_payload(value: object) -> TraceTelemetryMetadata | None:
    if not isinstance(value, dict):
        return None
    try:
        return TraceTelemetryMetadata.model_validate(value)
    except ValidationError:
        return None
