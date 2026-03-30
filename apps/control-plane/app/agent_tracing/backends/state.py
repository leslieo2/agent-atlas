from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.modules.shared.domain.traces import TraceSpan


class TraceSpanRepository(Protocol):
    def list_for_run(self, run_id: str | UUID) -> list[TraceSpan]: ...


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


__all__ = ["StateTraceBackend", "TraceSpanRepository"]
