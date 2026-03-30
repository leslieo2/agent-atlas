from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from app.modules.shared.application.contracts import RunTraceLookup


class _RunRecordView(Protocol):
    run_id: UUID
    created_at: datetime


class _RunReader(Protocol):
    def get(self, run_id: str | UUID) -> _RunRecordView | None: ...


class StateRunTraceLookup:
    def __init__(self, run_repository: _RunReader) -> None:
        self.run_repository = run_repository

    def get(self, run_id):
        run = self.run_repository.get(run_id)
        if run is None:
            return None
        return RunTraceLookup(
            run_id=run.run_id,
            created_at=run.created_at,
        )


__all__ = ["StateRunTraceLookup"]
