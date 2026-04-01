from __future__ import annotations

from typing import cast
from uuid import UUID

from app.db.persistence import StatePersistence
from app.infrastructure.repositories.common import persistence
from app.modules.shared.application.ports import TaskQueuePort
from app.modules.shared.domain.tasks import QueuedTask

state_persistence = cast(StatePersistence, persistence)


class StateTaskQueue(TaskQueuePort):
    def enqueue(self, task: QueuedTask) -> None:
        state_persistence.enqueue_task(task)

    def claim_next(self, worker_name: str, lease_seconds: int) -> QueuedTask | None:
        return state_persistence.claim_next_task(worker_name, lease_seconds)

    def mark_done(self, task_id: UUID) -> None:
        state_persistence.mark_task_done(task_id)

    def mark_failed(self, task_id: UUID, error: str) -> None:
        state_persistence.mark_task_failed(task_id, error)
