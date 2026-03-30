from __future__ import annotations

from uuid import uuid4

from app.modules.execution.domain.models import CancelRequest
from app.modules.runs.adapters.outbound.execution import (
    K8sJobExecutionAdapter,
    K8sJobLaunchRequest,
    LocalWorkerExecutionAdapter,
)
from app.modules.runs.domain.models import RunRecord, RunSpec
from app.modules.runs.domain.policies import RunAggregate
from app.modules.shared.domain.enums import AdapterKind, RunStatus
from app.modules.shared.domain.tasks import QueuedTask


class StubRunRepository:
    def __init__(self) -> None:
        self.saved: dict[object, RunRecord] = {}

    def get(self, run_id: object) -> RunRecord | None:
        return self.saved.get(run_id)

    def list(self) -> list[RunRecord]:
        return list(self.saved.values())

    def save(self, run: RunRecord) -> None:
        self.saved[run.run_id] = run


class StubTaskQueue:
    def __init__(self) -> None:
        self.enqueued: list[QueuedTask] = []

    def enqueue(self, task: QueuedTask) -> None:
        self.enqueued.append(task)

    def claim_next(self, worker_name: str, lease_seconds: int) -> QueuedTask | None:
        return None

    def mark_done(self, task_id) -> None:
        return None

    def mark_failed(self, task_id, error: str) -> None:
        return None


def _spec() -> RunSpec:
    return RunSpec(
        run_id=uuid4(),
        project="control-plane",
        dataset="dataset-v1",
        agent_id="basic",
        model="gpt-5.4-mini",
        entrypoint="app.agent_plugins.basic:build_agent",
        agent_type=AdapterKind.OPENAI_AGENTS,
        input_summary="run input",
        prompt="Summarize this run.",
    )


def test_submit_run_returns_opaque_handle_and_is_idempotent_for_active_run() -> None:
    repository = StubRunRepository()
    queue = StubTaskQueue()
    adapter = LocalWorkerExecutionAdapter(task_queue=queue, run_repository=repository)
    spec = _spec()
    run = RunAggregate.create(spec)
    repository.save(run)

    first = adapter.submit_run(spec)
    repository.save(
        repository.get(spec.run_id).model_copy(
            update={
                "attempt_id": first.attempt_id,
                "executor_backend": first.backend,
                "executor_submission_id": first.executor_ref,
            }
        )
    )
    second = adapter.submit_run(spec)

    assert len(queue.enqueued) == 1
    assert first.run_id == spec.run_id
    assert first.executor_ref.startswith("local-")
    assert second.attempt_id == first.attempt_id
    assert second.executor_ref == first.executor_ref


def test_cancel_run_only_updates_control_plane_status_and_hides_backend_details() -> None:
    repository = StubRunRepository()
    queue = StubTaskQueue()
    adapter = LocalWorkerExecutionAdapter(task_queue=queue, run_repository=repository)
    spec = _spec()
    run = RunAggregate.create(spec).model_copy(
        update={
            "executor_backend": "local-runner",
            "executor_submission_id": "local-ref",
        }
    )
    repository.save(run)

    cancelled = adapter.cancel_run(
        CancelRequest(
            run_id=run.run_id,
            attempt_id=run.attempt_id,
            reason="cancelled by experiment",
        )
    )
    status = adapter.get_status(run.run_id)

    assert cancelled is True
    assert status is not None
    assert status.status == RunStatus.CANCELLED
    assert status.backend == "local-runner"
    assert status.executor_ref == "local-ref"
    assert status.terminal_summary is not None
    assert status.terminal_summary.reason_message == "cancelled by experiment"


def test_retry_run_resubmits_same_run_as_new_attempt() -> None:
    repository = StubRunRepository()
    queue = StubTaskQueue()
    adapter = LocalWorkerExecutionAdapter(task_queue=queue, run_repository=repository)
    spec = _spec()
    run = RunAggregate.create(spec).model_copy(
        update={
            "status": RunStatus.FAILED,
            "executor_backend": "local-runner",
            "executor_submission_id": "local-ref",
            "latency_ms": 42,
            "token_cost": 9,
            "tool_calls": 1,
            "error_code": "provider_call",
            "error_message": "bad key",
            "termination_reason": "bad key",
            "terminal_reason": "bad key",
        }
    )
    repository.save(run)

    handle = adapter.retry_run(run.run_id)
    updated = repository.get(run.run_id)

    assert handle is not None
    assert len(queue.enqueued) == 1
    assert updated is not None
    assert updated.status == RunStatus.QUEUED
    assert updated.attempt == 2
    assert updated.attempt_id == handle.attempt_id
    assert updated.executor_submission_id == handle.executor_ref
    assert updated.latency_ms == 0
    assert updated.error_code is None


def test_k8s_execution_adapter_uses_launcher_job_name_for_executor_ref() -> None:
    repository = StubRunRepository()
    queue = StubTaskQueue()
    spec = _spec()
    spec = spec.model_copy(
        update={"executor_config": spec.executor_config.model_copy(update={"backend": "k8s-job"})}
    )
    repository.save(RunAggregate.create(spec))

    class StubK8sLauncher:
        def __init__(self) -> None:
            self.calls: list[tuple[object, int]] = []

        def build_request(self, payload):
            self.calls.append((payload.run_id, payload.attempt))
            return K8sJobLaunchRequest(
                job_name="atlas-run-custom",
                namespace="atlas-tests",
                config_map_name="atlas-run-custom-input",
                image="python:3.12-slim",
                config_map_manifest={},
                job_manifest={},
            )

    launcher = StubK8sLauncher()
    adapter = K8sJobExecutionAdapter(
        task_queue=queue,
        run_repository=repository,
        launcher=launcher,
    )

    handle = adapter.submit_run(spec)

    assert handle.executor_ref == "atlas-run-custom"
    assert launcher.calls == [(spec.run_id, 1)]
    assert len(queue.enqueued) == 1
