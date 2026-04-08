from __future__ import annotations

from uuid import UUID

from app.execution.application import (
    ExperimentAggregationService,
    ExperimentExecutionService,
    RunExecutionService,
)
from app.modules.runs.domain.models import RunExecutionSpec
from app.modules.shared.domain.jobs import EnqueuedExecutionJob, ExecutionJobKind


class ExecutionJobHandlers:
    def __init__(
        self,
        *,
        run_execution_service: RunExecutionService,
        experiment_execution_service: ExperimentExecutionService,
        experiment_aggregation_service: ExperimentAggregationService,
    ) -> None:
        self.run_execution_service = run_execution_service
        self.experiment_execution_service = experiment_execution_service
        self.experiment_aggregation_service = experiment_aggregation_service

    def dispatch(self, job: EnqueuedExecutionJob) -> None:
        if job.kind == ExecutionJobKind.RUN_EXECUTION:
            run_spec = RunExecutionSpec.model_validate(job.kwargs["run_spec"])
            self.run_execution_service.execute_run(run_spec.run_id, run_spec)
            return
        if job.kind == ExecutionJobKind.EXPERIMENT_EXECUTION:
            self.experiment_execution_service.execute_experiment(
                UUID(str(job.kwargs["experiment_id"]))
            )
            return
        if job.kind == ExecutionJobKind.EXPERIMENT_AGGREGATION:
            self.experiment_aggregation_service.refresh_experiment(
                UUID(str(job.kwargs["experiment_id"]))
            )
            return

        raise ValueError(f"unsupported execution job kind={job.kind.value}")
