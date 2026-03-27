from __future__ import annotations

from dataclasses import dataclass

from app.bootstrap.wiring.agents import AgentModuleBundle
from app.bootstrap.wiring.infrastructure import InfrastructureBundle
from app.bootstrap.wiring.runs import RunModuleBundle
from app.infrastructure.adapters.evals import StateEvalRunGateway
from app.modules.evals.application.execution import (
    EvalAggregationService,
    EvalExecutionService,
)
from app.modules.evals.application.use_cases import EvalJobCommands, EvalJobQueries


@dataclass(frozen=True)
class EvalModuleBundle:
    eval_run_gateway: StateEvalRunGateway
    eval_queries: EvalJobQueries
    eval_commands: EvalJobCommands
    eval_execution_service: EvalExecutionService
    eval_aggregation_service: EvalAggregationService


def build_eval_module(
    infra: InfrastructureBundle,
    agents: AgentModuleBundle,
    runs: RunModuleBundle,
) -> EvalModuleBundle:
    eval_run_gateway = StateEvalRunGateway(
        run_repository=infra.run_repository,
        trajectory_repository=infra.trajectory_repository,
        agent_catalog=infra.runnable_agent_catalog,
        run_submission=runs.run_submission,
    )
    eval_queries = EvalJobQueries(
        eval_job_repository=infra.eval_job_repository,
        sample_result_repository=infra.eval_sample_result_repository,
    )
    eval_commands = EvalJobCommands(
        eval_job_repository=infra.eval_job_repository,
        dataset_source=infra.dataset_repository,
        agent_lookup=agents.agent_lookup,
        task_queue=infra.task_queue,
    )
    eval_execution_service = EvalExecutionService(
        eval_job_repository=infra.eval_job_repository,
        dataset_source=infra.dataset_repository,
        eval_run_gateway=eval_run_gateway,
        task_queue=infra.task_queue,
    )
    eval_aggregation_service = EvalAggregationService(
        eval_job_repository=infra.eval_job_repository,
        sample_result_repository=infra.eval_sample_result_repository,
        dataset_source=infra.dataset_repository,
        eval_run_gateway=eval_run_gateway,
        task_queue=infra.task_queue,
    )

    return EvalModuleBundle(
        eval_run_gateway=eval_run_gateway,
        eval_queries=eval_queries,
        eval_commands=eval_commands,
        eval_execution_service=eval_execution_service,
        eval_aggregation_service=eval_aggregation_service,
    )
