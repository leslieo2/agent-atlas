from __future__ import annotations

from uuid import uuid4

from app.modules.runs.domain.models import ExecutionMetrics, RunRecord, RunSpec, utc_now
from app.modules.shared.domain.enums import RunStatus
from app.modules.shared.domain.models import RunLineage


class RunAggregate:
    def __init__(self, run: RunRecord) -> None:
        self.run = run

    @classmethod
    def create(cls, spec: RunSpec) -> RunRecord:
        return RunRecord(
            run_id=spec.run_id,
            attempt_id=uuid4(),
            experiment_id=spec.experiment_id,
            dataset_version_id=spec.dataset_version_id,
            input_summary=spec.input_summary,
            status=RunStatus.QUEUED,
            project=spec.project,
            dataset=spec.dataset,
            dataset_sample_id=spec.dataset_sample_id,
            agent_id=spec.agent_id,
            model=spec.model,
            entrypoint=spec.entrypoint,
            agent_type=spec.agent_type,
            tags=spec.tags,
            project_metadata={
                **spec.project_metadata,
                "prompt": spec.prompt,
            },
            artifact_ref=spec.provenance.artifact_ref if spec.provenance else None,
            image_ref=spec.provenance.image_ref if spec.provenance else None,
            executor_backend=spec.executor_config.backend,
            runner_backend=spec.provenance.runner_backend if spec.provenance else None,
            provenance=spec.provenance.model_copy(deep=True) if spec.provenance else None,
            lineage=RunLineage(
                experiment_id=spec.experiment_id,
                dataset_name=spec.dataset,
                dataset_version_id=spec.dataset_version_id,
                dataset_sample_id=spec.dataset_sample_id,
            ),
        )

    @classmethod
    def load(cls, run: RunRecord) -> RunAggregate:
        return cls(run)

    def mark_starting(self) -> RunRecord:
        if self.run.status != RunStatus.QUEUED:
            raise ValueError(f"cannot start run from status={self.run.status.value}")
        now = utc_now()
        self.run.status = RunStatus.STARTING
        self.run.started_at = self.run.started_at or now
        self.run.last_heartbeat_at = now
        self.run.last_progress_at = now
        self.run.heartbeat_sequence += 1
        self.run.termination_reason = None
        self.run.terminal_reason = None
        return self.run

    def mark_running(self) -> RunRecord:
        if self.run.status not in {RunStatus.QUEUED, RunStatus.STARTING}:
            raise ValueError(f"cannot start run from status={self.run.status.value}")
        now = utc_now()
        self.run.status = RunStatus.RUNNING
        self.run.started_at = self.run.started_at or now
        self.run.last_heartbeat_at = now
        self.run.last_progress_at = now
        self.run.heartbeat_sequence += 1
        self.run.termination_reason = None
        self.run.terminal_reason = None
        return self.run

    def mark_succeeded(self) -> RunRecord:
        if self.run.status not in {RunStatus.RUNNING, RunStatus.STARTING, RunStatus.QUEUED}:
            raise ValueError(f"cannot succeed run from status={self.run.status.value}")
        now = utc_now()
        self.run.status = RunStatus.SUCCEEDED
        self.run.started_at = self.run.started_at or now
        self.run.completed_at = now
        self.run.last_heartbeat_at = now
        self.run.last_progress_at = now
        self.run.heartbeat_sequence += 1
        self.run.termination_reason = None
        self.run.terminal_reason = None
        return self.run

    def mark_failed(self, reason: str | None = None) -> RunRecord:
        if self.run.status in {RunStatus.SUCCEEDED, RunStatus.CANCELLED, RunStatus.LOST}:
            raise ValueError(f"cannot fail run from status={self.run.status.value}")
        now = utc_now()
        self.run.status = RunStatus.FAILED
        self.run.started_at = self.run.started_at or now
        self.run.completed_at = now
        self.run.last_heartbeat_at = now
        self.run.last_progress_at = now
        self.run.heartbeat_sequence += 1
        self.run.termination_reason = reason
        self.run.terminal_reason = reason
        return self.run

    def record_metrics(self, metrics: ExecutionMetrics) -> RunRecord:
        self.run.latency_ms += metrics.latency_ms
        self.run.token_cost += metrics.token_cost
        self.run.tool_calls += metrics.tool_calls
        return self.run

    def update_model(self, model: str | None = None) -> RunRecord:
        self.run.resolved_model = model
        return self.run

    def update_execution_runtime(
        self,
        *,
        artifact_ref: str | None,
        image_ref: str | None,
        runner_backend: str | None,
        execution_backend: str | None,
        container_image: str | None,
    ) -> RunRecord:
        self.run.artifact_ref = artifact_ref
        self.run.image_ref = image_ref
        self.run.runner_backend = runner_backend
        self.run.execution_backend = execution_backend
        self.run.container_image = container_image
        if self.run.provenance is not None:
            self.run.provenance.artifact_ref = artifact_ref
            self.run.provenance.image_ref = image_ref
            self.run.provenance.runner_backend = runner_backend
        self.run.error_code = None
        self.run.error_message = None
        if self.run.status not in {RunStatus.CANCELLING, RunStatus.CANCELLED}:
            self.run.termination_reason = None
            self.run.terminal_reason = None
        return self.run

    def record_failure(
        self,
        *,
        error_code: str,
        error_message: str,
    ) -> RunRecord:
        self.run.error_code = error_code
        self.run.error_message = error_message
        return self.run

    def request_cancel(self, reason: str = "cancelled by user") -> RunRecord:
        if self.run.status not in {
            RunStatus.QUEUED,
            RunStatus.STARTING,
            RunStatus.RUNNING,
            RunStatus.CANCELLING,
        }:
            raise ValueError(f"cannot cancel run from status={self.run.status.value}")
        self.run.status = (
            RunStatus.CANCELLED
            if self.run.status in {RunStatus.QUEUED, RunStatus.STARTING}
            else RunStatus.CANCELLING
        )
        now = utc_now()
        self.run.last_heartbeat_at = now
        self.run.last_progress_at = now
        self.run.heartbeat_sequence += 1
        self.run.termination_reason = reason
        self.run.terminal_reason = reason
        if self.run.status == RunStatus.CANCELLED:
            self.run.completed_at = now
        return self.run

    def mark_cancelled(self, reason: str = "cancelled by user") -> RunRecord:
        if self.run.status not in {
            RunStatus.QUEUED,
            RunStatus.STARTING,
            RunStatus.RUNNING,
            RunStatus.CANCELLING,
        }:
            raise ValueError(f"cannot cancel run from status={self.run.status.value}")
        now = utc_now()
        self.run.status = RunStatus.CANCELLED
        self.run.completed_at = now
        self.run.last_heartbeat_at = now
        self.run.last_progress_at = now
        self.run.heartbeat_sequence += 1
        self.run.termination_reason = reason
        self.run.terminal_reason = reason
        return self.run

    def mark_lost(self, reason: str = "execution heartbeat lost") -> RunRecord:
        if self.run.status in {RunStatus.SUCCEEDED, RunStatus.FAILED, RunStatus.CANCELLED}:
            raise ValueError(f"cannot lose run from status={self.run.status.value}")
        now = utc_now()
        self.run.status = RunStatus.LOST
        self.run.completed_at = now
        self.run.last_heartbeat_at = now
        self.run.last_progress_at = now
        self.run.heartbeat_sequence += 1
        self.run.termination_reason = reason
        self.run.terminal_reason = reason
        return self.run
