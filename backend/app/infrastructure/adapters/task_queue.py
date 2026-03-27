from __future__ import annotations

from uuid import UUID

from app.infrastructure.repositories.common import persistence
from app.modules.shared.application.ports import TaskQueuePort
from app.modules.shared.domain.tasks import QueuedTask


class StateTaskQueue(TaskQueuePort):
    def enqueue(self, task: QueuedTask) -> None:
        persistence.enqueue_task(task)

    def claim_next(self, worker_name: str, lease_seconds: int) -> QueuedTask | None:
        return persistence.claim_next_task(worker_name, lease_seconds)

    def mark_done(self, task_id: UUID) -> None:
        persistence.mark_task_done(task_id)

    def mark_failed(self, task_id: UUID, error: str) -> None:
        persistence.mark_task_failed(task_id, error)
