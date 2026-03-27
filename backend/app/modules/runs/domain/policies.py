from __future__ import annotations

from app.modules.runs.domain.models import ExecutionMetrics, RunRecord, RunSpec
from app.modules.shared.domain.enums import RunStatus


class RunAggregate:
    def __init__(self, run: RunRecord) -> None:
        self.run = run

    @classmethod
    def create(cls, spec: RunSpec) -> RunRecord:
        return RunRecord(
            input_summary=spec.input_summary,
            status=RunStatus.QUEUED,
            project=spec.project,
            dataset=spec.dataset,
            eval_job_id=spec.eval_job_id,
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
        )

    @classmethod
    def load(cls, run: RunRecord) -> RunAggregate:
        return cls(run)

    def mark_running(self) -> RunRecord:
        if self.run.status != RunStatus.QUEUED:
            raise ValueError(f"cannot start run from status={self.run.status.value}")
        self.run.status = RunStatus.RUNNING
        self.run.termination_reason = None
        return self.run

    def mark_succeeded(self) -> RunRecord:
        if self.run.status not in {RunStatus.RUNNING, RunStatus.QUEUED}:
            raise ValueError(f"cannot succeed run from status={self.run.status.value}")
        self.run.status = RunStatus.SUCCEEDED
        self.run.termination_reason = None
        return self.run

    def mark_failed(self, reason: str | None = None) -> RunRecord:
        if self.run.status in {RunStatus.SUCCEEDED, RunStatus.TERMINATED}:
            raise ValueError(f"cannot fail run from status={self.run.status.value}")
        self.run.status = RunStatus.FAILED
        self.run.termination_reason = reason
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
        execution_backend: str | None,
        container_image: str | None,
    ) -> RunRecord:
        self.run.execution_backend = execution_backend
        self.run.container_image = container_image
        self.run.error_code = None
        self.run.error_message = None
        if self.run.status != RunStatus.TERMINATED:
            self.run.termination_reason = None
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

    def terminate(self, reason: str = "terminated by user") -> RunRecord:
        if self.run.status not in {RunStatus.QUEUED, RunStatus.RUNNING}:
            raise ValueError(f"cannot terminate run from status={self.run.status.value}")
        self.run.status = RunStatus.TERMINATED
        self.run.termination_reason = reason
        self.run.artifact_ref = None
        return self.run
