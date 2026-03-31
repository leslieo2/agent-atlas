from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, ValidationError

from agent_atlas_contracts.execution import (
    ArtifactManifest,
    EventEnvelope,
    ProducerInfo,
    RunnerRunSpec,
    TerminalMetrics,
    TerminalResult,
)


def utc_now() -> datetime:
    return datetime.now(UTC)


class AgentLoadFailedError(Exception):
    def __init__(self, message: str, **context: str) -> None:
        self.message = message
        self.context = {key: value for key, value in context.items() if value}
        super().__init__(self.message)


class StepType(str, Enum):
    LLM = "llm"
    TOOL = "tool"
    PLANNER = "planner"
    MEMORY = "memory"


class ExecutionReferenceMetadata(BaseModel):
    artifact_ref: str | None = None
    image_ref: str | None = None


class AgentManifest(BaseModel):
    agent_id: str
    name: str
    description: str
    framework: str
    framework_version: str = "1.0.0"
    default_model: str
    tags: list[str] = Field(default_factory=list)
    capabilities: list[str] = Field(default_factory=list)


class AgentBuildContext(BaseModel):
    run_id: UUID
    project: str
    dataset: str | None = None
    prompt: str
    tags: list[str] = Field(default_factory=list)
    project_metadata: dict[str, Any] = Field(default_factory=dict)


class PublishedAgent(BaseModel):
    manifest: AgentManifest
    entrypoint: str
    published_at: datetime = Field(default_factory=utc_now)
    source_fingerprint: str = ""
    execution_reference: ExecutionReferenceMetadata = Field(
        default_factory=ExecutionReferenceMetadata
    )
    default_runtime_profile: dict[str, Any] = Field(
        default_factory=lambda: {"backend": "k8s-job"}
    )

    @property
    def agent_id(self) -> str:
        return self.manifest.agent_id

    @property
    def name(self) -> str:
        return self.manifest.name

    @property
    def description(self) -> str:
        return self.manifest.description

    @property
    def framework(self) -> str:
        return self.manifest.framework

    @property
    def default_model(self) -> str:
        return self.manifest.default_model

    @property
    def tags(self) -> list[str]:
        return list(self.manifest.tags)

    @property
    def framework_version(self) -> str:
        return self.manifest.framework_version

    @property
    def capabilities(self) -> list[str]:
        return list(self.manifest.capabilities)

    def to_snapshot(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class TraceTelemetryMetadata(BaseModel):
    agent_id: str | None = None
    framework: str | None = None
    framework_type: str | None = None
    framework_version: str | None = None
    artifact_ref: str | None = None
    image_ref: str | None = None
    runner_backend: str | None = None
    executor_backend: str | None = None
    experiment_id: UUID | None = None
    dataset_version_id: UUID | None = None
    dataset_sample_id: str | None = None
    prompt_version: str | None = None
    image_digest: str | None = None


class TraceIngestEvent(BaseModel):
    run_id: UUID
    span_id: str
    parent_span_id: str | None = None
    step_type: StepType = StepType.LLM
    name: str
    input: dict[str, Any]
    output: dict[str, Any] = Field(default_factory=dict)
    tool_name: str | None = None
    latency_ms: int = 0
    token_usage: int = 0
    image_digest: str | None = None
    prompt_version: str | None = None
    metadata: TraceTelemetryMetadata | None = None


class RuntimeExecutionResult(BaseModel):
    output: str
    latency_ms: int
    token_usage: int
    provider: str
    execution_backend: str | None = None
    container_image: str | None = None
    resolved_model: str | None = None


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
    experiment_id: UUID | None,
    attempt: int,
    attempt_id: UUID | None,
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


def usage_total_tokens(usage: object) -> int:
    if usage is None:
        return 0
    if isinstance(usage, dict):
        return int(usage.get("total_tokens", 0) or 0)
    return int(getattr(usage, "total_tokens", 0) or 0)


def extract_error_message(value: object) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        for key in ("message", "detail", "error_description"):
            candidate = value.get(key)
            if isinstance(candidate, str) and candidate.strip():
                return candidate.strip()
        for nested in _iter_mapping_values(value):
            message = extract_error_message(nested)
            if message:
                return message
        return ""
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        for item in value:
            message = extract_error_message(item)
            if message:
                return message
    return ""


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


def _iter_mapping_values(value: object) -> Sequence[object]:
    if isinstance(value, Mapping):
        return list(value.values())
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        return list(value)
    return []


__all__ = [
    "AgentBuildContext",
    "AgentLoadFailedError",
    "AgentManifest",
    "ExecutionReferenceMetadata",
    "PublishedAgent",
    "PublishedRunExecutionResult",
    "RuntimeExecutionResult",
    "StepType",
    "TraceIngestEvent",
    "TraceTelemetryMetadata",
    "empty_artifact_manifest",
    "event_envelope_to_trace_event",
    "event_envelopes_to_trace_events",
    "extract_error_message",
    "producer_for_runtime",
    "terminal_result_from_runtime_result",
    "trace_event_to_event_envelope",
    "usage_total_tokens",
]
