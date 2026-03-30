from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID

from app.infrastructure.adapters.phoenix import (
    build_phoenix_project_url,
    build_phoenix_trace_url,
)
from app.modules.shared.domain.enums import StepType
from app.modules.shared.domain.models import ObservabilityMetadata
from app.modules.shared.domain.traces import TraceIngestEvent, TraceSpan


def _safe_json_dumps(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _normalize_base_url(base_url: str | None) -> str | None:
    if not base_url:
        return None
    return base_url.rstrip("/")


class StateTraceBackend:
    def __init__(
        self,
        *,
        repository: TraceSpanRepository,
        backend_name: str = "state",
    ) -> None:
        self.repository = repository
        self._backend_name = backend_name

    def list_for_run(self, run_id: str | UUID) -> list[TraceSpan]:
        return [
            span
            if span.trace_backend
            else span.model_copy(update={"trace_backend": self._backend_name})
            for span in self.repository.list_for_run(run_id)
        ]

    def backend_name(self) -> str:
        return self._backend_name


class TraceSpanRepository(Protocol):
    def list_for_run(self, run_id: str | UUID) -> list[TraceSpan]: ...


class NoopTraceExporter:
    def export(
        self,
        events: list[TraceIngestEvent],
        spans: list[TraceSpan],
    ) -> ObservabilityMetadata | None:
        del events, spans
        return None


class OtlpTraceExporter:
    def __init__(
        self,
        *,
        endpoint: str,
        project_name: str,
        backend_name: str = "otlp",
        base_url: str | None = None,
        headers: dict[str, str] | None = None,
        api_key: str | None = None,
        service_name: str = "agent-atlas-control-plane",
    ) -> None:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import SimpleSpanProcessor

        resource = Resource.create(
            {
                "service.name": service_name,
                "atlas.project_name": project_name,
            }
        )
        self.provider = TracerProvider(resource=resource)
        self.provider.add_span_processor(
            SimpleSpanProcessor(
                OTLPSpanExporter(endpoint=endpoint, headers=dict(headers or {})),
            )
        )
        self.tracer = self.provider.get_tracer("agent_atlas.observability")
        self.backend_name_value = backend_name
        self.base_url = _normalize_base_url(base_url)
        self.project_name = project_name
        self.api_key = api_key
        self.project_id: str | None = None
        self.client = self._build_backend_client()

    def export(
        self,
        events: list[TraceIngestEvent],
        spans: list[TraceSpan],
    ) -> ObservabilityMetadata | None:
        if not events or not spans:
            return None

        from opentelemetry.trace import NonRecordingSpan, Status, StatusCode, set_span_in_context

        contexts: dict[str, NonRecordingSpan] = {}
        trace_id: str | None = None
        base_time_ns = int(datetime.now(UTC).timestamp() * 1_000_000_000)

        for index, (event, span) in enumerate(zip(events, spans, strict=True)):
            parent_span = contexts.get(event.parent_span_id or "")
            context = set_span_in_context(parent_span) if parent_span is not None else None
            start_time = base_time_ns + (index * 1_000_000)
            end_time = start_time + max(span.latency_ms, 1) * 1_000_000
            otel_span = self.tracer.start_span(
                name=event.name,
                context=context,
                start_time=start_time,
                attributes=self._attributes(event, span),
            )
            error_message = event.output.get("error")
            if event.output.get("success") is False:
                otel_span.set_status(
                    Status(StatusCode.ERROR, str(error_message or "trace export error"))
                )
            else:
                otel_span.set_status(Status(StatusCode.OK))
            otel_span.end(end_time=end_time)
            contexts[event.span_id] = NonRecordingSpan(otel_span.get_span_context())
            if trace_id is None:
                trace_id = f"{otel_span.get_span_context().trace_id:032x}"

        self.provider.force_flush()
        first_event = events[0]
        project_id = self._resolve_project_id()
        return ObservabilityMetadata(
            backend=self.backend_name_value,
            trace_id=trace_id,
            trace_url=build_phoenix_trace_url(
                base_url=self.base_url,
                project_id=project_id,
                trace_id=trace_id,
            )
            if self.backend_name_value == "phoenix"
            else None,
            project_url=build_phoenix_project_url(
                base_url=self.base_url,
                project_id=project_id,
                experiment_id=first_event.metadata.experiment_id if first_event.metadata else None,
                run_id=first_event.run_id,
            )
            if self.backend_name_value == "phoenix"
            else None,
        )

    def _attributes(self, event: TraceIngestEvent, span: TraceSpan) -> dict[str, Any]:
        metadata = event.metadata
        step_kind = "TOOL" if event.step_type == StepType.TOOL else "LLM"
        return {
            "openinference.span.kind": step_kind,
            "input.value": event.input.get("prompt")
            if isinstance(event.input.get("prompt"), str)
            else _safe_json_dumps(event.input),
            "output.value": event.output.get("output")
            if isinstance(event.output.get("output"), str)
            else _safe_json_dumps(event.output),
            "tool.name": event.tool_name,
            "atlas.run_id": str(event.run_id),
            "atlas.span_id": event.span_id,
            "atlas.parent_span_id": event.parent_span_id,
            "atlas.step_type": event.step_type.value,
            "atlas.agent_id": metadata.agent_id if metadata else None,
            "atlas.framework": metadata.framework if metadata else None,
            "atlas.framework_type": metadata.framework_type if metadata else None,
            "atlas.framework_version": metadata.framework_version if metadata else None,
            "atlas.artifact_ref": metadata.artifact_ref if metadata else None,
            "atlas.image_ref": metadata.image_ref if metadata else None,
            "atlas.runner_backend": metadata.runner_backend if metadata else None,
            "atlas.executor_backend": metadata.executor_backend if metadata else None,
            "atlas.experiment_id": str(metadata.experiment_id)
            if metadata and metadata.experiment_id
            else None,
            "atlas.dataset_version_id": str(metadata.dataset_version_id)
            if metadata and metadata.dataset_version_id
            else None,
            "atlas.dataset_sample_id": metadata.dataset_sample_id if metadata else None,
            "atlas.prompt_version": span.prompt_version,
            "atlas.image_digest": span.image_digest,
            "atlas.tool_name": event.tool_name,
            "atlas.latency_ms": span.latency_ms,
            "atlas.token_usage": span.token_usage,
            "atlas.input_json": _safe_json_dumps(event.input),
            "atlas.output_json": _safe_json_dumps(event.output),
            "atlas.received_at": span.received_at.isoformat(),
        }

    def _build_backend_client(self) -> Any | None:
        if self.backend_name_value != "phoenix" or self.base_url is None:
            return None
        try:
            from phoenix.client import Client
        except ImportError:
            return None
        return Client(base_url=self.base_url, api_key=self.api_key)

    def _resolve_project_id(self) -> str | None:
        if self.project_id:
            return self.project_id
        if self.client is None:
            return None
        try:
            project = self.client.projects.get(project_name=self.project_name)
        except Exception:
            return None
        self.project_id = getattr(project, "id", None)
        return self.project_id


__all__ = [
    "NoopTraceExporter",
    "OtlpTraceExporter",
    "StateTraceBackend",
]
