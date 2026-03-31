from __future__ import annotations

from dataclasses import dataclass

from app.bootstrap.wiring.agents import AgentModuleBundle
from app.bootstrap.wiring.infrastructure import InfrastructureBundle
from app.bootstrap.wiring.runs import RunModuleBundle
from app.modules.experiments.application.execution import (
    ExperimentAggregationService,
    ExperimentOrchestrator,
)
from app.modules.experiments.application.use_cases import ExperimentCommands, ExperimentQueries


@dataclass(frozen=True)
class ExperimentModuleBundle:
    experiment_queries: ExperimentQueries
    experiment_commands: ExperimentCommands
    experiment_orchestrator: ExperimentOrchestrator
    experiment_aggregation_service: ExperimentAggregationService


def build_experiment_module(
    infra: InfrastructureBundle,
    agents: AgentModuleBundle,
    runs: RunModuleBundle,
) -> ExperimentModuleBundle:
    experiment_queries = ExperimentQueries(
        experiment_repository=infra.experiment_repository,
        run_evaluation_repository=infra.run_evaluation_repository,
        run_repository=infra.run_repository,
        dataset_repository=infra.dataset_repository,
    )
    experiment_commands = ExperimentCommands(
        experiment_repository=infra.experiment_repository,
        run_evaluation_repository=infra.run_evaluation_repository,
        dataset_repository=infra.dataset_repository,
        run_repository=infra.run_repository,
        approval_policy_repository=infra.approval_policy_repository,
        execution_control=infra.execution.execution_control,
        task_queue=infra.execution.task_queue,
        agent_exists=agents.agent_exists,
    )
    experiment_orchestrator = ExperimentOrchestrator(
        experiment_repository=infra.experiment_repository,
        dataset_repository=infra.dataset_repository,
        agent_catalog=infra.runnable_agent_catalog,
        run_submission=runs.run_submission,
        task_queue=infra.execution.task_queue,
    )
    experiment_aggregation_service = ExperimentAggregationService(
        experiment_repository=infra.experiment_repository,
        run_evaluation_repository=infra.run_evaluation_repository,
        dataset_repository=infra.dataset_repository,
        run_repository=infra.run_repository,
        trajectory_repository=infra.tracing.trajectory_repository,
        task_queue=infra.execution.task_queue,
    )
    return ExperimentModuleBundle(
        experiment_queries=experiment_queries,
        experiment_commands=experiment_commands,
        experiment_orchestrator=experiment_orchestrator,
        experiment_aggregation_service=experiment_aggregation_service,
    )
