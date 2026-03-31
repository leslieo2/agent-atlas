from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any, cast
from urllib.parse import quote, urlencode
from uuid import UUID

from app.agent_tracing.contracts import RunTraceLookupPort
from app.modules.shared.domain.enums import StepType
from app.modules.shared.domain.traces import TraceSpan


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


class PhoenixTraceLinkResolver:
    def __init__(
        self,
        *,
        base_url: str,
        project_name: str,
        api_key: str | None = None,
    ) -> None:
        self.base_url = _normalize_base_url(base_url)
        self.project_name = project_name
        self.project_id: str | None = None
        self.client = self._build_client(base_url=base_url, api_key=api_key)

    def build_trace_url(self, trace_id: str | None) -> str | None:
        return build_phoenix_trace_url(
            base_url=self.base_url,
            project_id=self._resolve_project_id(),
            trace_id=trace_id,
        )

    def build_project_url(
        self,
        *,
        experiment_id: str | UUID | None = None,
        run_id: str | UUID | None = None,
    ) -> str | None:
        return build_phoenix_project_url(
            base_url=self.base_url,
            project_id=self._resolve_project_id(),
            experiment_id=experiment_id,
            run_id=run_id,
        )

    @staticmethod
    def _build_client(*, base_url: str, api_key: str | None) -> object | None:
        try:
            from phoenix.client import Client
        except ImportError:
            return None
        return Client(base_url=base_url, api_key=api_key)

    def _resolve_project_id(self) -> str | None:
        if self.project_id:
            return self.project_id
        if self.client is None:
            return None
        try:
            project = cast(Any, self.client).projects.get(project_name=self.project_name)
        except Exception:
            return None
        self.project_id = getattr(project, "id", None)
        return self.project_id


class PhoenixTraceBackend:
    def __init__(
        self,
        *,
        run_lookup: RunTraceLookupPort,
        base_url: str,
        project_name: str,
        api_key: str | None = None,
        query_limit: int = 500,
    ) -> None:
        from phoenix.client import Client

        self.run_lookup = run_lookup
        self.client = Client(base_url=base_url, api_key=api_key)
        self.project_name = project_name
        self.query_limit = query_limit

    def list_for_run(self, run_id: str | UUID) -> list[TraceSpan]:
        run = self.run_lookup.get(run_id)
        start_time = run.created_at if run else None
        raw_spans = [
            self._coerce_raw_span(raw_span)
            for raw_span in self.client.spans.get_spans(
                project_identifier=self.project_name,
                start_time=start_time,
                limit=self.query_limit,
            )
        ]
        return [span for span in raw_spans if str(span.run_id) == str(run_id)]

    @staticmethod
    def backend_name() -> str:
        return "phoenix"

    def _coerce_raw_span(self, raw_span: object) -> TraceSpan:
        record = raw_span if isinstance(raw_span, dict) else getattr(raw_span, "__dict__", {})
        attributes = record.get("attributes") if isinstance(record, dict) else {}
        attributes = attributes if isinstance(attributes, dict) else {}

        span_id = str(attributes.get("atlas.span_id") or record.get("id") or "")
        run_id = UUID(str(attributes.get("atlas.run_id")))
        parent_span_id = attributes.get("atlas.parent_span_id")
        raw_step_type = str(attributes.get("atlas.step_type") or StepType.LLM.value)
        try:
            step_type = StepType(raw_step_type)
        except ValueError:
            step_type = StepType.LLM
        tool_name = attributes.get("atlas.tool_name")
        input_payload = _safe_json_loads(attributes.get("atlas.input_json"))
        output_payload = _safe_json_loads(attributes.get("atlas.output_json"))
        received_at = attributes.get("atlas.received_at") or record.get("end_time")
        parsed_received_at = (
            datetime.fromisoformat(str(received_at)) if received_at else datetime.now(UTC)
        )

        return TraceSpan(
            run_id=run_id,
            span_id=span_id,
            parent_span_id=str(parent_span_id) if parent_span_id else None,
            step_type=step_type,
            input=input_payload,
            output=output_payload,
            tool_name=str(tool_name) if tool_name else None,
            latency_ms=_coerce_int(attributes.get("atlas.latency_ms")),
            token_usage=_coerce_int(attributes.get("atlas.token_usage")),
            image_digest=(
                str(attributes.get("atlas.image_digest"))
                if attributes.get("atlas.image_digest")
                else None
            ),
            prompt_version=(
                str(attributes.get("atlas.prompt_version"))
                if attributes.get("atlas.prompt_version")
                else None
            ),
            trace_backend="phoenix",
            received_at=parsed_received_at,
        )


__all__ = [
    "PhoenixTraceBackend",
    "PhoenixTraceLinkResolver",
    "build_phoenix_project_url",
    "build_phoenix_trace_url",
]
