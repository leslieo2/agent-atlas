from __future__ import annotations

from uuid import UUID

from app.infrastructure.repositories.runs import StateTraceRepository
from app.modules.traces.domain.models import TraceSpan


class AtlasStateTraceBackend:
    def __init__(self, repository: StateTraceRepository | None = None) -> None:
        self.repository = repository or StateTraceRepository()

    def list_for_run(self, run_id: str | UUID) -> list[TraceSpan]:
        return self.repository.list_for_run(run_id)

    def append(self, span: TraceSpan) -> None:
        self.repository.append(span)

    def backend_name(self) -> str:
        return "atlas-state"
