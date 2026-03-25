from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.modules.shared.domain.tasks import QueuedTask


class TaskQueuePort(Protocol):
    def enqueue(self, task: QueuedTask) -> None: ...

    def claim_next(self, worker_name: str, lease_seconds: int) -> QueuedTask | None: ...

    def mark_done(self, task_id: UUID) -> None: ...

    def mark_failed(self, task_id: UUID, error: str) -> None: ...


__all__ = ["TaskQueuePort"]
