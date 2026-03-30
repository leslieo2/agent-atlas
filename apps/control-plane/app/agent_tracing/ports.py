from __future__ import annotations

from typing import Protocol
from uuid import UUID


class TraceLinkResolverPort(Protocol):
    def build_trace_url(self, trace_id: str | None) -> str | None: ...

    def build_project_url(
        self,
        *,
        experiment_id: str | UUID | None = None,
        run_id: str | UUID | None = None,
    ) -> str | None: ...
