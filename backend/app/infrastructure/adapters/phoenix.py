from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote, urlencode
from uuid import UUID

from app.modules.runs.application.ports import RunRepository
from app.modules.shared.domain.enums import StepType
from app.modules.shared.domain.models import ObservabilityMetadata
from app.modules.traces.domain.models import TraceIngestEvent, TraceSpan


def _safe_json_dumps(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _safe_json_loads(value: object) -> dict[str, object]:
    if not isinstance(value, str) or not value.strip():
        return {}
    try:
        loaded = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _coerce_int(value: object, default: int = 0) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(float(value))
        except ValueError:
            return default
    return default


def _normalize_base_url(base_url: str | None) -> str | None:
    if not base_url:
        return None
    return base_url.rstrip("/")


def build_phoenix_project_url(
    *,
    base_url: str | None,
    project_id: str | None,
    experiment_id: str | UUID | None = None,
    run_id: str | UUID | None = None,
) -> str | None:
    normalized_base_url = _normalize_base_url(base_url)
    if not normalized_base_url:
        return None
    if not project_id:
        return normalized_base_url
    path = f"{normalized_base_url}/projects/{quote(project_id, safe='')}"
    params: dict[str, str] = {}
    if experiment_id is not None:
        params["experiment_id"] = str(experiment_id)
    if run_id is not None:
        params["run_id"] = str(run_id)
    if not params:
        return path
    return f"{path}?{urlencode(params)}"


def build_phoenix_trace_url(
    *,
    base_url: str | None,
    project_id: str | None,
    trace_id: str | None,
) -> str | None:
    normalized_base_url = _normalize_base_url(base_url)
    if not normalized_base_url or not project_id or not trace_id:
        return None
    project_path = quote(project_id, safe="")
    trace_path = quote(trace_id, safe="")
    return f"{normalized_base_url}/projects/{project_path}/traces/{trace_path}"


class NoopTraceExporter:
    def export(
        self,
        events: list[TraceIngestEvent],
        spans: list[TraceSpan],
    ) -> ObservabilityMetadata | None:
        return None


class PhoenixTraceExporter:
    def __init__(
        self,
        *,
        endpoint: str,
        project_name: str,
        base_url: str | None = None,
        api_key: str | None = None,
    ) -> None:
        from opentelemetry import trace
        from phoenix.client import Client
        from phoenix.otel import register

        register(
            endpoint=endpoint,
            project_name=project_name,
            batch=False,
            auto_instrument=False,
            verbose=False,
            api_key=api_key,
        )
        self.trace = trace
        self.tracer = trace.get_tracer("agent_atlas.phoenix")
        self.base_url = _normalize_base_url(base_url)
        self.project_name = project_name
        self.project_id: str | None = None
        self.client = Client(base_url=base_url, api_key=api_key) if base_url else None

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
        base_time_ns = datetime.now(UTC).timestamp()
        base_time_ns = int(base_time_ns * 1_000_000_000)

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

        first_event = events[0]
        project_id = self._resolve_project_id()
        return ObservabilityMetadata(
            backend="phoenix",
            trace_id=trace_id,
            trace_url=build_phoenix_trace_url(
                base_url=self.base_url,
                project_id=project_id,
                trace_id=trace_id,
            ),
            project_url=build_phoenix_project_url(
                base_url=self.base_url,
                project_id=project_id,
                experiment_id=first_event.metadata.experiment_id if first_event.metadata else None,
                run_id=first_event.run_id,
            ),
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

    def _resolve_project_id(self) -> str | None:
        if self.project_id:
            return self.project_id
        if self.client is None:
            return None
        try:
            project = self.client.projects.get(project_name=self.project_name)
        except Exception:
            return None
        self.project_id = _extract_project_id(project)
        return self.project_id


class PhoenixTraceBackend:
    def __init__(
        self,
        *,
        run_repository: RunRepository,
        base_url: str,
        project_name: str,
        api_key: str | None = None,
        query_limit: int = 500,
    ) -> None:
        from phoenix.client import Client

        self.run_repository = run_repository
        self.client = Client(base_url=base_url, api_key=api_key)
        self.project_name = project_name
        self.query_limit = query_limit

    def list_for_run(self, run_id: str | UUID) -> list[TraceSpan]:
        run = self.run_repository.get(run_id)
        start_time = run.created_at if run else None
        raw_spans = [
            self._coerce_raw_span(raw_span)
            for raw_span in self.client.spans.get_spans(
                project_identifier=self.project_name,
                start_time=start_time,
                limit=self.query_limit,
            )
        ]
        normalized_run_id = str(run_id)
        matching_spans = [
            raw_span
            for raw_span in raw_spans
            if self._attribute(raw_span, "atlas.run_id") == normalized_run_id
        ]
        return [
            self._to_trace_span(raw_span)
            for raw_span in sorted(matching_spans, key=self._span_sort_key)
        ]

    def backend_name(self) -> str:
        return "phoenix"

    def _span_sort_key(self, raw_span: dict[str, Any]) -> tuple[str, str]:
        start_time = raw_span.get("start_time")
        span_id = self._attribute(raw_span, "atlas.span_id") or str(raw_span.get("id") or "")
        return str(start_time or ""), span_id

    def _to_trace_span(self, raw_span: dict[str, Any]) -> TraceSpan:
        input_payload = _safe_json_loads(self._attribute(raw_span, "atlas.input_json"))
        output_payload = _safe_json_loads(self._attribute(raw_span, "atlas.output_json"))
        received_at_raw = self._attribute(raw_span, "atlas.received_at") or raw_span.get("end_time")
        received_at = datetime.now(UTC)
        if isinstance(received_at_raw, str) and received_at_raw:
            try:
                received_at = datetime.fromisoformat(
                    received_at_raw.replace("Z", "+00:00")
                ).astimezone(UTC)
            except ValueError:
                received_at = datetime.now(UTC)
        step_type_raw = self._attribute(raw_span, "atlas.step_type") or StepType.LLM.value
        return TraceSpan(
            run_id=UUID(str(self._attribute(raw_span, "atlas.run_id"))),
            span_id=str(self._attribute(raw_span, "atlas.span_id") or raw_span.get("id") or ""),
            parent_span_id=self._attribute(raw_span, "atlas.parent_span_id"),
            step_type=StepType(step_type_raw),
            input=input_payload,
            output=output_payload,
            tool_name=self._attribute(raw_span, "atlas.tool_name"),
            latency_ms=_coerce_int(self._attribute(raw_span, "atlas.latency_ms")),
            token_usage=_coerce_int(self._attribute(raw_span, "atlas.token_usage")),
            image_digest=self._attribute(raw_span, "atlas.image_digest"),
            prompt_version=self._attribute(raw_span, "atlas.prompt_version"),
            trace_backend="phoenix",
            received_at=received_at,
        )

    @staticmethod
    def _attribute(raw_span: dict[str, Any], key: str) -> Any:
        attributes = raw_span.get("attributes") or {}
        if isinstance(attributes, dict):
            return attributes.get(key)
        return None

    @staticmethod
    def _coerce_raw_span(raw_span: object) -> dict[str, Any]:
        if isinstance(raw_span, dict):
            return raw_span
        return {
            "id": getattr(raw_span, "id", None),
            "start_time": getattr(raw_span, "start_time", None),
            "end_time": getattr(raw_span, "end_time", None),
            "attributes": getattr(raw_span, "attributes", None) or {},
        }


def _extract_project_id(project: object) -> str | None:
    if isinstance(project, dict):
        project_id = project.get("id")
        return str(project_id) if project_id else None
    project_id = getattr(project, "id", None)
    return str(project_id) if project_id else None
