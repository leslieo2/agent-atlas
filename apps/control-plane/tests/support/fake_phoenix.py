from __future__ import annotations

from typing import Any
from uuid import UUID

from app.agent_tracing.backends.phoenix import (
    build_phoenix_project_url,
    build_phoenix_trace_url,
)
from app.infrastructure.repositories import StateTraceRepository
from app.modules.shared.domain.models import TracingMetadata
from app.modules.shared.domain.traces import TraceIngestEvent, TraceSpan


class FakeOtlpTraceExporter:
    def __init__(
        self,
        *,
        endpoint: str,
        project_name: str,
        backend_name: str = "phoenix",
        base_url: str | None = None,
        headers: dict[str, str] | None = None,
        api_key: str | None = None,
        timeout: float | None = None,
        service_name: str = "agent-atlas-control-plane",
        link_resolver: Any | None = None,
    ) -> None:
        del headers, api_key, timeout, service_name
        resolved_base_url = base_url
        if resolved_base_url is None and endpoint:
            resolved_base_url = endpoint.removesuffix("/v1/traces")
        self.base_url = resolved_base_url.rstrip("/") if resolved_base_url else None
        self.project_name = project_name
        self.project_id = f"project-{project_name}"
        self.backend_name_value = backend_name
        self.link_resolver = link_resolver

    def export(
        self,
        events: list[TraceIngestEvent],
        spans: list[TraceSpan],
    ) -> TracingMetadata | None:
        del spans
        if not events:
            return None
        first_event = events[0]
        trace_id = f"trace-{first_event.run_id}"
        if self.link_resolver is not None:
            trace_url = self.link_resolver.build_trace_url(trace_id)
            project_url = self.link_resolver.build_project_url(
                experiment_id=first_event.metadata.experiment_id if first_event.metadata else None,
                run_id=first_event.run_id,
            )
            if trace_url is None:
                trace_url = build_phoenix_trace_url(
                    base_url=self.base_url,
                    project_id=self.project_id,
                    trace_id=trace_id,
                )
            if project_url is None or project_url == self.base_url:
                project_url = build_phoenix_project_url(
                    base_url=self.base_url,
                    project_id=self.project_id,
                    experiment_id=(
                        first_event.metadata.experiment_id if first_event.metadata else None
                    ),
                    run_id=first_event.run_id,
                )
        else:
            trace_url = build_phoenix_trace_url(
                base_url=self.base_url,
                project_id=self.project_id,
                trace_id=trace_id,
            )
            project_url = build_phoenix_project_url(
                base_url=self.base_url,
                project_id=self.project_id,
                experiment_id=first_event.metadata.experiment_id if first_event.metadata else None,
                run_id=first_event.run_id,
            )
        return TracingMetadata(
            backend=self.backend_name_value,
            trace_id=trace_id,
            trace_url=trace_url,
            project_url=project_url,
        )


class FakePhoenixTraceBackend:
    def __init__(
        self,
        *,
        run_repository: Any,
        base_url: str,
        project_name: str,
        api_key: str | None = None,
        query_limit: int = 500,
        repository: StateTraceRepository | None = None,
    ) -> None:
        del run_repository, base_url, project_name, api_key, query_limit
        self.repository = repository or StateTraceRepository()

    def list_for_run(self, run_id: str | UUID) -> list[TraceSpan]:
        return [
            span.model_copy(update={"trace_backend": "phoenix"})
            for span in self.repository.list_for_run(run_id)
        ]

    def backend_name(self) -> str:
        return "phoenix"
