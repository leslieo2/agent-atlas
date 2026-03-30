from __future__ import annotations

from uuid import UUID

from agent_atlas_contracts.execution import ExecutionHandoff
from app.execution.application.ports import ExecutionAttempt, ExecutionOutcomeSinkPort
from app.execution.application.service import ProjectedExecutionRecord, RunFailureDetails
from app.modules.runs.application.ports import RunObservationSinkPort, RunRepository
from app.modules.runs.application.results import RunnerExecutionResult
from app.modules.runs.domain.policies import RunAggregate
from app.modules.shared.domain.enums import RunStatus


class RunExecutionStateSink(ExecutionOutcomeSinkPort):
    def __init__(
        self,
        run_repository: RunRepository,
        observation_sink: RunObservationSinkPort,
    ) -> None:
        self.run_repository = run_repository
        self.observation_sink = observation_sink

    def load_attempt(self, run_id: UUID) -> ExecutionAttempt:
        run = self.run_repository.get(run_id)
        if run is None:
            return ExecutionAttempt(attempt=1, attempt_id=None)
        return ExecutionAttempt(attempt=run.attempt, attempt_id=run.attempt_id)

    def transition_status(
        self,
        run_id: UUID,
        status: RunStatus,
        reason: str | None = None,
    ) -> bool:
        run = self.run_repository.get(run_id)
        if not run:
            return False

        aggregate = RunAggregate.load(run)
        try:
            if status == RunStatus.STARTING:
                updated = aggregate.mark_starting()
            elif status == RunStatus.RUNNING:
                updated = aggregate.mark_running()
            elif status == RunStatus.SUCCEEDED:
                updated = aggregate.mark_succeeded()
            elif status == RunStatus.FAILED:
                updated = aggregate.mark_failed(reason)
            else:
                raise ValueError(f"unsupported status transition target={status.value}")
        except ValueError:
            return False

        self.run_repository.save(updated)
        return True

    def mark_cancelled_if_requested(self, run_id: UUID) -> bool:
        run = self.run_repository.get(run_id)
        if not run or run.status != RunStatus.CANCELLING:
            return False
        reason = run.termination_reason or "cancelled by user"
        try:
            updated = RunAggregate.load(run).mark_cancelled(reason)
        except ValueError:
            return False
        self.run_repository.save(updated)
        return True

    def record_execution_handoff(
        self,
        run_id: UUID,
        handoff: ExecutionHandoff,
    ) -> None:
        run = self.run_repository.get(run_id)
        if not run:
            return
        aggregate = RunAggregate.load(run)
        updated = aggregate.update_execution_runtime(
            artifact_ref=handoff.artifact_ref,
            image_ref=handoff.image_ref,
            runner_backend=handoff.runner_backend,
            execution_backend=run.execution_backend,
            container_image=run.container_image,
        )
        self.run_repository.save(updated)

    def record_runner_result(
        self,
        run_id: UUID,
        result: RunnerExecutionResult,
    ) -> None:
        run = self.run_repository.get(run_id)
        if not run:
            return
        aggregate = RunAggregate.load(run)
        aggregate.update_model(result.execution.runtime_result.resolved_model)
        updated = aggregate.update_execution_runtime(
            artifact_ref=result.artifact_ref,
            image_ref=result.image_ref,
            runner_backend=result.runner_backend,
            execution_backend=result.execution.runtime_result.execution_backend,
            container_image=result.execution.runtime_result.container_image,
        )
        self.run_repository.save(updated)

    def record_projected_execution(
        self,
        run_id: UUID,
        record: ProjectedExecutionRecord,
    ) -> None:
        if record.events:
            self.observation_sink.ingest_many(record.events)

        run = self.run_repository.get(run_id)
        if not run:
            return
        updated = RunAggregate.load(run).record_metrics(record.metrics)
        self.run_repository.save(updated)

    def record_failure(
        self,
        run_id: UUID,
        failure: RunFailureDetails,
    ) -> None:
        run = self.run_repository.get(run_id)
        if not run:
            return
        updated = RunAggregate.load(run).record_failure(
            error_code=failure.code,
            error_message=failure.message,
        )
        self.run_repository.save(updated)
