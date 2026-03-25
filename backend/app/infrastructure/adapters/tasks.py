from __future__ import annotations

from uuid import UUID

from app.db.state import state
from app.modules.shared.domain.tasks import QueuedTask


class StateTaskQueue:
    def enqueue(self, task: QueuedTask) -> None:
        state.persist.enqueue_task(task)

    def claim_next(self, worker_name: str, lease_seconds: int) -> QueuedTask | None:
        return state.persist.claim_next_task(worker_name, lease_seconds)

    def mark_done(self, task_id: UUID) -> None:
        state.persist.mark_task_done(task_id)

    def mark_failed(self, task_id: UUID, error: str) -> None:
        state.persist.mark_task_failed(task_id, error)
