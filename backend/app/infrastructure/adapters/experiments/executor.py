from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol
from uuid import UUID

from app.core.errors import UnsupportedOperationError
from app.modules.experiments.application.ports import (
    ExecutorCapability,
    ExecutorPort,
    ExecutorSubmission,
    ExecutorSyncResult,
)
from app.modules.runs.application.ports import RunRepository
from app.modules.runs.domain.models import RunSpec
from app.modules.runs.domain.policies import RunAggregate
from app.modules.shared.application.ports import TaskQueuePort
from app.modules.shared.domain.tasks import QueuedTask, TaskType


class _ExecutorAdapter(Protocol):
    def submit(self, run_spec: RunSpec) -> ExecutorSubmission: ...

    def cancel(self, run_id: str | UUID) -> bool: ...

    def sync(self, run_id: str | UUID) -> ExecutorSyncResult | None: ...

    def capability(self) -> ExecutorCapability: ...


class _QueuedExecutorAdapter:
    def __init__(
        self,
        *,
        backend: str,
        task_queue: TaskQueuePort,
        run_repository: RunRepository,
        production_ready: bool,
    ) -> None:
        self.backend = backend
        self.task_queue = task_queue
        self.run_repository = run_repository
        self.production_ready = production_ready

    def submit(self, run_spec: RunSpec) -> ExecutorSubmission:
        self.task_queue.enqueue(
            QueuedTask(
                task_type=TaskType.RUN_EXECUTION,
                target_id=run_spec.run_id,
                payload=run_spec.model_dump(mode="json"),
            )
        )
        prefix = "job" if self.backend == "k8s-job" else "local"
        return ExecutorSubmission(backend=self.backend, submission_id=f"{prefix}-{run_spec.run_id}")

    def cancel(self, run_id: str | UUID) -> bool:
        run = self.run_repository.get(run_id)
        if run is None:
            return False
        try:
            cancelled = RunAggregate.load(run).terminate("cancelled by executor")
        except ValueError:
            return False
        self.run_repository.save(cancelled)
        return True

    def sync(self, run_id: str | UUID) -> ExecutorSyncResult | None:
        run = self.run_repository.get(run_id)
        if run is None:
            return None
        return ExecutorSyncResult(run_id=run.run_id, backend=self.backend, status=run.status)

    def capability(self) -> ExecutorCapability:
        return ExecutorCapability(
            backend=self.backend,
            production_ready=self.production_ready,
            supports_cancel=True,
            supports_sync=True,
        )


class LocalRunnerExecutorAdapter(_QueuedExecutorAdapter):
    def __init__(self, *, task_queue: TaskQueuePort, run_repository: RunRepository) -> None:
        super().__init__(
            backend="local-runner",
            task_queue=task_queue,
            run_repository=run_repository,
            production_ready=False,
        )


class K8sJobExecutorAdapter(_QueuedExecutorAdapter):
    def __init__(self, *, task_queue: TaskQueuePort, run_repository: RunRepository) -> None:
        super().__init__(
            backend="k8s-job",
            task_queue=task_queue,
            run_repository=run_repository,
            production_ready=True,
        )


class ExecutorRegistry(ExecutorPort):
    def __init__(self, executors: Mapping[str, _ExecutorAdapter]) -> None:
        self.executors = {key.strip().lower(): value for key, value in executors.items()}

    def submit(self, run_spec: RunSpec) -> ExecutorSubmission:
        backend = run_spec.executor_config.backend.strip().lower()
        executor = self.executors.get(backend)
        if executor is None:
            raise UnsupportedOperationError(
                f"executor backend '{run_spec.executor_config.backend}' is not configured",
                executor_backend=run_spec.executor_config.backend,
            )
        return executor.submit(run_spec)

    def cancel(self, run_id: str | UUID) -> bool:
        return any(executor.cancel(run_id) for executor in self.executors.values())

    def sync(self, run_id: str | UUID) -> ExecutorSyncResult | None:
        for executor in self.executors.values():
            result = executor.sync(run_id)
            if result is not None:
                return result
        return None

    def capabilities(self) -> list[ExecutorCapability]:
        return [executor.capability() for executor in self.executors.values()]
