from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import UTC, datetime

from agent_atlas_contracts.execution import RunnerRunSpec
from agent_atlas_contracts.runtime import StepType, TraceIngestEvent


def _safe_json_dumps(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def emit_trace_events_to_otlp(
    *,
    payload: RunnerRunSpec,
    events: Sequence[TraceIngestEvent],
    service_name: str,
) -> None:
    tracing = payload.tracing
    export = tracing.export if tracing is not None else None
    if export is None or not export.endpoint or not events:
        return

    try:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import SimpleSpanProcessor
        from opentelemetry.trace import NonRecordingSpan, Status, StatusCode, set_span_in_context
    except ImportError:
        return

    provider = TracerProvider(
        resource=Resource.create(
            {
                "service.name": service_name,
                "atlas.project_name": tracing.project_name,
                "atlas.run_id": str(payload.run_id),
                "atlas.agent_id": payload.agent_id,
            }
        )
    )
    provider.add_span_processor(
        SimpleSpanProcessor(
            OTLPSpanExporter(
                endpoint=export.endpoint,
                headers=dict(export.headers),
            )
        )
    )
    tracer = provider.get_tracer(service_name)
    contexts: dict[str, NonRecordingSpan] = {}
    base_time_ns = int(datetime.now(UTC).timestamp() * 1_000_000_000)

    for index, event in enumerate(events):
        parent_span = contexts.get(event.parent_span_id or "")
        context = set_span_in_context(parent_span) if parent_span is not None else None
        start_time = base_time_ns + (index * 1_000_000)
        end_time = start_time + max(event.latency_ms, 1) * 1_000_000
        span = tracer.start_span(
            name=event.name,
            context=context,
            start_time=start_time,
            attributes=_attributes(payload=payload, event=event),
        )
        error_message = event.output.get("error")
        if event.output.get("success") is False:
            span.set_status(Status(StatusCode.ERROR, str(error_message or "runtime trace error")))
        else:
            span.set_status(Status(StatusCode.OK))
        span.end(end_time=end_time)
        contexts[event.span_id] = NonRecordingSpan(span.get_span_context())

    provider.force_flush()


def _attributes(
    *,
    payload: RunnerRunSpec,
    event: TraceIngestEvent,
) -> dict[str, object]:
    metadata = event.metadata
    return {
        "openinference.span.kind": "TOOL" if event.step_type == StepType.TOOL else "LLM",
        "input.value": event.input.get("prompt")
        if isinstance(event.input.get("prompt"), str)
        else _safe_json_dumps(event.input),
        "output.value": event.output.get("output")
        if isinstance(event.output.get("output"), str)
        else _safe_json_dumps(event.output),
        "tool.name": event.tool_name,
        "atlas.run_id": str(payload.run_id),
        "atlas.experiment_id": str(payload.experiment_id) if payload.experiment_id else None,
        "atlas.agent_id": payload.agent_id,
        "atlas.framework": payload.framework,
        "atlas.trace_backend": payload.trace_backend,
        "atlas.span_id": event.span_id,
        "atlas.parent_span_id": event.parent_span_id,
        "atlas.step_type": event.step_type.value,
        "atlas.dataset_version_id": str(payload.dataset_version_id)
        if payload.dataset_version_id
        else None,
        "atlas.dataset_sample_id": payload.dataset_sample_id,
        "atlas.prompt_version": event.prompt_version
        or (metadata.prompt_version if metadata else None),
        "atlas.image_digest": event.image_digest or (metadata.image_digest if metadata else None),
        "atlas.runner_backend": metadata.runner_backend if metadata else None,
        "atlas.executor_backend": metadata.executor_backend if metadata else None,
        "atlas.latency_ms": event.latency_ms,
        "atlas.token_usage": event.token_usage,
        "atlas.input_json": _safe_json_dumps(event.input),
        "atlas.output_json": _safe_json_dumps(event.output),
    }


__all__ = ["emit_trace_events_to_otlp"]
