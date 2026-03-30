from __future__ import annotations

from typing import Any
from uuid import UUID

from app.modules.shared.domain.models import TracingMetadata
from app.tracing.backends.phoenix import (
    build_phoenix_project_url,
    build_phoenix_trace_url,
)
from app.infrastructure.repositories import StateTraceRepository
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
        service_name: str = "agent-atlas-control-plane",
    ) -> None:
        del endpoint, headers, api_key, service_name
        self.base_url = base_url.rstrip("/") if base_url else None
        self.project_name = project_name
        self.project_id = f"project-{project_name}"
        self.backend_name_value = backend_name

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
        return TracingMetadata(
            backend=self.backend_name_value,
            trace_id=trace_id,
            trace_url=build_phoenix_trace_url(
                base_url=self.base_url,
                project_id=self.project_id,
                trace_id=trace_id,
            ),
            project_url=build_phoenix_project_url(
                base_url=self.base_url,
                project_id=self.project_id,
                experiment_id=first_event.metadata.experiment_id if first_event.metadata else None,
                run_id=first_event.run_id,
            ),
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
