from __future__ import annotations

from uuid import UUID

from app.execution.application import RunExecutionService
from app.modules.experiments.application.execution import (
    ExperimentAggregationService,
    ExperimentOrchestrator,
)
from app.modules.runs.domain.models import RunExecutionSpec as ExecutionRunSpec
from app.modules.shared.domain.jobs import EnqueuedExecutionJob, ExecutionJobKind


class ExecutionJobHandlers:
    def __init__(
        self,
        *,
        run_execution_service: RunExecutionService,
        experiment_orchestrator: ExperimentOrchestrator,
        experiment_aggregation_service: ExperimentAggregationService,
    ) -> None:
        self.run_execution_service = run_execution_service
        self.experiment_orchestrator = experiment_orchestrator
        self.experiment_aggregation_service = experiment_aggregation_service

    def dispatch(self, job: EnqueuedExecutionJob) -> None:
        if job.kind == ExecutionJobKind.RUN_EXECUTION:
            run_spec = ExecutionRunSpec.model_validate(job.kwargs["run_spec"])
            self.run_execution_service.execute_run(run_spec.run_id, run_spec)
            return
        if job.kind == ExecutionJobKind.EXPERIMENT_EXECUTION:
            self.experiment_orchestrator.execute_experiment(UUID(str(job.kwargs["experiment_id"])))
            return
        if job.kind == ExecutionJobKind.EXPERIMENT_AGGREGATION:
            self.experiment_aggregation_service.refresh_experiment(
                UUID(str(job.kwargs["experiment_id"]))
            )
            return

        raise ValueError(f"unsupported execution job kind={job.kind.value}")
