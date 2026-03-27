from __future__ import annotations

import socket
import time
from uuid import uuid4

from app.core.config import settings
from app.modules.evals.application.execution import (
    EvalAggregationService,
    EvalExecutionService,
)
from app.modules.runs.application.execution import RunExecutionService
from app.modules.runs.domain.models import RunSpec
from app.modules.shared.application.ports import TaskQueuePort
from app.modules.shared.domain.tasks import QueuedTask, TaskType


class AppWorker:
    def __init__(
        self,
        task_queue: TaskQueuePort,
        run_execution_service: RunExecutionService,
        eval_execution_service: EvalExecutionService,
        eval_aggregation_service: EvalAggregationService,
    ) -> None:
        self.task_queue = task_queue
        self.run_execution_service = run_execution_service
        self.eval_execution_service = eval_execution_service
        self.eval_aggregation_service = eval_aggregation_service

    def run_once(self, worker_name: str, lease_seconds: int) -> bool:
        task = self.task_queue.claim_next(worker_name, lease_seconds)
        if task is None:
            return False

        try:
            self._dispatch(task)
        except Exception as exc:
            self.task_queue.mark_failed(task.task_id, str(exc))
            return True

        self.task_queue.mark_done(task.task_id)
        return True

    def run_forever(
        self,
        worker_name: str | None = None,
        poll_interval_seconds: float | None = None,
        lease_seconds: int | None = None,
    ) -> None:
        resolved_worker_name = worker_name or self.default_worker_name()
        resolved_poll_interval = (
            poll_interval_seconds
            if poll_interval_seconds is not None
            else settings.worker_poll_interval_seconds
        )
        resolved_lease_seconds = (
            lease_seconds if lease_seconds is not None else settings.worker_task_lease_seconds
        )

        while True:
            processed = self.run_once(resolved_worker_name, resolved_lease_seconds)
            if not processed:
                time.sleep(max(0.1, resolved_poll_interval))

    @staticmethod
    def default_worker_name() -> str:
        if settings.worker_name:
            return settings.worker_name
        return f"{socket.gethostname()}-{uuid4().hex[:8]}"

    def _dispatch(self, task: QueuedTask) -> None:
        if task.task_type == TaskType.RUN_EXECUTION:
            self.run_execution_service.execute_run(
                task.target_id,
                RunSpec.model_validate(task.payload),
            )
            return
        if task.task_type == TaskType.EVAL_EXECUTION:
            self.eval_execution_service.execute_job(task.target_id)
            return
        if task.task_type == TaskType.EVAL_AGGREGATION:
            self.eval_aggregation_service.refresh_job(task.target_id)
            return

        raise ValueError(f"unsupported task_type={task.task_type.value}")
