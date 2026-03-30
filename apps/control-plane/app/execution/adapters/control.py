from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol
from uuid import UUID, uuid4

from app.core.errors import UnsupportedOperationError
from app.execution.adapters.launchers import K8sLauncher
from app.execution.application.ports import ExecutionControlPort
from app.execution.contracts import (
    CancelRequest,
    ExecutionCapability,
    Heartbeat,
    RunHandle,
    RunStatusSnapshot,
    RunTerminalSummary,
    runner_run_spec_from_run_spec,
)
from app.modules.runs.application.ports import RunRepository
from app.modules.runs.domain.models import RunSpec, utc_now
from app.modules.shared.application.ports import TaskQueuePort
from app.modules.shared.domain.enums import RunStatus
from app.modules.shared.domain.tasks import QueuedTask, TaskType


class _ExecutionBackendAdapter(Protocol):
    def submit_run(self, run_spec: RunSpec) -> RunHandle: ...

    def cancel_run(self, request: CancelRequest) -> bool: ...

    def retry_run(self, run_id: str | UUID) -> RunHandle | None: ...

    def get_status(self, run_id: str | UUID) -> RunStatusSnapshot | None: ...

    def capability(self) -> ExecutionCapability: ...


class _QueuedExecutionBackendAdapter:
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

    def submit_run(self, run_spec: RunSpec) -> RunHandle:
        existing = self.run_repository.get(run_spec.run_id)
        if (
            existing is not None
            and existing.executor_backend == self.backend
            and existing.executor_submission_id
            and existing.status
            in {
                RunStatus.QUEUED,
                RunStatus.STARTING,
                RunStatus.RUNNING,
                RunStatus.CANCELLING,
            }
        ):
            return RunHandle(
                run_id=existing.run_id,
                attempt_id=existing.attempt_id,
                backend=self.backend,
                executor_ref=existing.executor_submission_id,
                submitted_at=existing.created_at,
            )

        attempt = existing.attempt if existing is not None else 1
        attempt_id = uuid4()
        handle = RunHandle(
            run_id=run_spec.run_id,
            attempt_id=attempt_id,
            backend=self.backend,
            executor_ref=self._executor_ref(
                run_spec,
                attempt=attempt,
                attempt_id=attempt_id,
            ),
        )
        if existing is not None:
            self.run_repository.save(
                existing.model_copy(
                    update={
                        "attempt_id": handle.attempt_id,
                        "executor_backend": handle.backend,
                        "executor_submission_id": handle.executor_ref,
                    }
                )
            )
        self.task_queue.enqueue(
            QueuedTask(
                task_type=TaskType.RUN_EXECUTION,
                target_id=run_spec.run_id,
                payload=run_spec.model_dump(mode="json"),
            )
        )
        return handle

    def cancel_run(self, request: CancelRequest) -> bool:
        run = self.run_repository.get(request.run_id)
        if run is None or (request.attempt_id is not None and run.attempt_id != request.attempt_id):
            return False
        if run.status not in {
            RunStatus.QUEUED,
            RunStatus.STARTING,
            RunStatus.RUNNING,
            RunStatus.CANCELLING,
        }:
            return False
        now = utc_now()
        cancelled = run.model_copy(
            update={
                "status": (
                    RunStatus.CANCELLED
                    if run.status in {RunStatus.QUEUED, RunStatus.STARTING}
                    else RunStatus.CANCELLING
                ),
                "last_heartbeat_at": now,
                "last_progress_at": now,
                "heartbeat_sequence": run.heartbeat_sequence + 1,
                "termination_reason": request.reason,
                "terminal_reason": request.reason,
                "completed_at": now
                if run.status in {RunStatus.QUEUED, RunStatus.STARTING}
                else run.completed_at,
            }
        )
        self.run_repository.save(cancelled)
        return True

    def retry_run(self, run_id: str | UUID) -> RunHandle | None:
        run = self.run_repository.get(run_id)
        if run is None or run.status in {
            RunStatus.QUEUED,
            RunStatus.STARTING,
            RunStatus.RUNNING,
            RunStatus.CANCELLING,
        }:
            return None

        retry_spec = run.to_run_spec()
        retry_attempt = run.attempt + 1
        retry_attempt_id = uuid4()
        retry_handle = RunHandle(
            run_id=run.run_id,
            attempt_id=retry_attempt_id,
            backend=self.backend,
            executor_ref=self._executor_ref(
                retry_spec,
                attempt=retry_attempt,
                attempt_id=retry_attempt_id,
            ),
        )
        updated = run.model_copy(
            update={
                "attempt_id": retry_handle.attempt_id,
                "attempt": retry_attempt,
                "status": RunStatus.QUEUED,
                "latency_ms": 0,
                "token_cost": 0,
                "tool_calls": 0,
                "started_at": None,
                "completed_at": None,
                "error_code": None,
                "error_message": None,
                "termination_reason": None,
                "terminal_reason": None,
                "last_heartbeat_at": None,
                "last_progress_at": None,
                "lease_expires_at": None,
                "heartbeat_sequence": 0,
                "executor_backend": retry_handle.backend,
                "executor_submission_id": retry_handle.executor_ref,
            }
        )
        self.run_repository.save(updated)
        self.task_queue.enqueue(
            QueuedTask(
                task_type=TaskType.RUN_EXECUTION,
                target_id=retry_spec.run_id,
                payload=retry_spec.model_dump(mode="json"),
            )
        )
        return retry_handle

    def get_status(self, run_id: str | UUID) -> RunStatusSnapshot | None:
        run = self.run_repository.get(run_id)
        if run is None:
            return None

        terminal_summary = None
        if run.status in {
            RunStatus.SUCCEEDED,
            RunStatus.FAILED,
            RunStatus.CANCELLED,
            RunStatus.LOST,
        }:
            terminal_summary = RunTerminalSummary(
                run_id=run.run_id,
                attempt_id=run.attempt_id,
                status=run.status,
                backend=run.executor_backend or self.backend,
                reason_code=run.error_code,
                reason_message=run.terminal_reason or run.error_message,
                artifact_ref=run.artifact_ref,
                image_ref=run.image_ref,
                trace_url=run.trace_pointer.trace_url if run.trace_pointer else None,
                started_at=run.started_at,
                completed_at=run.completed_at or run.created_at,
            )

        heartbeat = None
        if run.last_heartbeat_at is not None:
            heartbeat = Heartbeat(
                run_id=run.run_id,
                attempt_id=run.attempt_id,
                backend=run.executor_backend or self.backend,
                sequence=run.heartbeat_sequence,
                status=run.status,
                occurred_at=run.last_heartbeat_at,
                lease_expires_at=run.lease_expires_at,
                last_progress_at=run.last_progress_at,
                phase_hint=run.status.value,
            )

        return RunStatusSnapshot(
            run_id=run.run_id,
            attempt_id=run.attempt_id,
            backend=run.executor_backend or self.backend,
            executor_ref=run.executor_submission_id,
            status=run.status,
            reason_code=run.error_code,
            reason_message=run.terminal_reason or run.error_message,
            heartbeat=heartbeat,
            terminal_summary=terminal_summary,
        )

    def capability(self) -> ExecutionCapability:
        return ExecutionCapability(
            backend=self.backend,
            production_ready=self.production_ready,
            supports_cancel=True,
            supports_retry=True,
            supports_status=True,
            supports_heartbeat=False,
        )

    def _executor_ref(
        self,
        run_spec: RunSpec,
        *,
        attempt: int,
        attempt_id: UUID,
    ) -> str:
        del attempt, attempt_id
        run_id = run_spec.run_id
        prefix = "job" if self.backend == "k8s-job" else "local"
        return f"{prefix}-{run_id}"


class LocalWorkerExecutionAdapter(_QueuedExecutionBackendAdapter):
    def __init__(self, *, task_queue: TaskQueuePort, run_repository: RunRepository) -> None:
        super().__init__(
            backend="local-runner",
            task_queue=task_queue,
            run_repository=run_repository,
            production_ready=False,
        )


class K8sJobExecutionAdapter(_QueuedExecutionBackendAdapter):
    def __init__(
        self,
        *,
        task_queue: TaskQueuePort,
        run_repository: RunRepository,
        launcher: K8sLauncher | None = None,
    ) -> None:
        super().__init__(
            backend="k8s-job",
            task_queue=task_queue,
            run_repository=run_repository,
            production_ready=False,
        )
        self.launcher = launcher or K8sLauncher()

    def submit_run(self, run_spec: RunSpec) -> RunHandle:
        handle = super().submit_run(run_spec)
        request = self.launcher.build_request(
            runner_run_spec_from_run_spec(run_spec, attempt_id=handle.attempt_id)
        )
        if request.job_name == handle.executor_ref:
            return handle

        run = self.run_repository.get(run_spec.run_id)
        if run is None:
            return handle.model_copy(update={"executor_ref": request.job_name})

        updated = run.model_copy(update={"executor_submission_id": request.job_name})
        self.run_repository.save(updated)
        return handle.model_copy(update={"executor_ref": request.job_name})


class ExecutionControlRegistry(ExecutionControlPort):
    def __init__(self, *, backends: Mapping[str, _ExecutionBackendAdapter]) -> None:
        self.backends = {key.strip().lower(): value for key, value in backends.items()}

    def submit_run(self, run_spec: RunSpec) -> RunHandle:
        backend_name = run_spec.executor_config.backend.strip().lower()
        backend = self.backends.get(backend_name)
        if backend is None:
            raise UnsupportedOperationError(
                f"execution backend '{run_spec.executor_config.backend}' is not configured",
                executor_backend=run_spec.executor_config.backend,
            )
        return backend.submit_run(run_spec)

    def cancel_run(self, request: CancelRequest) -> bool:
        return any(backend.cancel_run(request) for backend in self.backends.values())

    def retry_run(self, run_id: str | UUID) -> RunHandle | None:
        for backend in self.backends.values():
            retry = backend.retry_run(run_id)
            if retry is not None:
                return retry
        return None

    def get_status(self, run_id: str | UUID) -> RunStatusSnapshot | None:
        for backend in self.backends.values():
            status = backend.get_status(run_id)
            if status is not None:
                return status
        return None

    def capabilities(self) -> list[ExecutionCapability]:
        return [backend.capability() for backend in self.backends.values()]


__all__ = [
    "ExecutionControlRegistry",
    "K8sJobExecutionAdapter",
    "LocalWorkerExecutionAdapter",
]
