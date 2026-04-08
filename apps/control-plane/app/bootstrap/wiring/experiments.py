from __future__ import annotations

from dataclasses import dataclass

from app.bootstrap.wiring.agents import AgentModuleBundle
from app.bootstrap.wiring.infrastructure import InfrastructureBundle
from app.bootstrap.wiring.runs import RunModuleBundle
from app.execution.adapters.experiments import (
    RunBackedExperimentRunLookup,
    RunBackedExperimentRunQuery,
    RunSubmissionExperimentLauncher,
    TrajectoryRepositoryExperimentLookup,
)
from app.execution.application.experiments import (
    ExperimentAggregationService,
    ExperimentExecutionService,
)
from app.modules.experiments.adapters.outbound.policies import ApprovalPolicySnapshotResolver
from app.modules.experiments.application.use_cases import ExperimentCommands, ExperimentQueries


@dataclass(frozen=True)
class ExperimentModuleBundle:
    experiment_queries: ExperimentQueries
    experiment_commands: ExperimentCommands
    experiment_execution_service: ExperimentExecutionService
    experiment_aggregation_service: ExperimentAggregationService


def build_experiment_module(
    infra: InfrastructureBundle,
    agents: AgentModuleBundle,
    runs: RunModuleBundle,
) -> ExperimentModuleBundle:
    run_lookup = RunBackedExperimentRunLookup(run_repository=infra.run_repository)
    experiment_queries = ExperimentQueries(
        experiment_repository=infra.experiment_repository,
        run_query=RunBackedExperimentRunQuery(
            dataset_repository=infra.dataset_repository,
            run_repository=infra.run_repository,
            run_evaluation_repository=infra.run_evaluation_repository,
        ),
        run_evaluation_repository=infra.run_evaluation_repository,
    )
    experiment_commands = ExperimentCommands(
        experiment_repository=infra.experiment_repository,
        run_evaluation_repository=infra.run_evaluation_repository,
        dataset_repository=infra.dataset_repository,
        run_lookup=run_lookup,
        approval_policy_resolver=ApprovalPolicySnapshotResolver(
            approval_policy_repository=infra.approval_policy_repository,
        ),
        execution_control=infra.execution.execution_control,
        job_queue=infra.execution.job_queue,
        agent_catalog=infra.published_agent_catalog,
    )
    experiment_execution_service = ExperimentExecutionService(
        experiment_repository=infra.experiment_repository,
        dataset_repository=infra.dataset_repository,
        agent_catalog=infra.published_agent_catalog,
        run_launcher=RunSubmissionExperimentLauncher(run_submission=runs.run_submission),
        job_queue=infra.execution.job_queue,
    )
    experiment_aggregation_service = ExperimentAggregationService(
        experiment_repository=infra.experiment_repository,
        run_evaluation_repository=infra.run_evaluation_repository,
        dataset_repository=infra.dataset_repository,
        run_lookup=run_lookup,
        trajectory_lookup=TrajectoryRepositoryExperimentLookup(
            trajectory_repository=infra.tracing.trajectory_repository,
        ),
        job_queue=infra.execution.job_queue,
    )
    return ExperimentModuleBundle(
        experiment_queries=experiment_queries,
        experiment_commands=experiment_commands,
        experiment_execution_service=experiment_execution_service,
        experiment_aggregation_service=experiment_aggregation_service,
    )
