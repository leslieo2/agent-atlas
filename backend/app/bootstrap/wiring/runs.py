from __future__ import annotations

from dataclasses import dataclass

from app.bootstrap.wiring.infrastructure import InfrastructureBundle
from app.bootstrap.wiring.traces import TraceModuleBundle
from app.modules.runs.application.execution import RunExecutionService
from app.modules.runs.application.services import RunSubmissionService
from app.modules.runs.application.telemetry import (
    RunTelemetryIngestionService,
    TrajectoryRecorder,
)
from app.modules.runs.application.use_cases import RunCommands, RunQueries


@dataclass(frozen=True)
class RunModuleBundle:
    run_submission: RunSubmissionService
    telemetry_ingestor: RunTelemetryIngestionService
    run_queries: RunQueries
    run_commands: RunCommands
    run_execution_service: RunExecutionService


def build_run_module(
    infra: InfrastructureBundle,
    traces: TraceModuleBundle,
) -> RunModuleBundle:
    run_submission = RunSubmissionService(
        run_repository=infra.run_repository,
        task_queue=infra.task_queue,
    )
    telemetry_ingestor = RunTelemetryIngestionService(
        trace_ingestor=traces.trace_commands,
        trajectory_recorder=TrajectoryRecorder(
            trajectory_repository=infra.trajectory_repository,
            step_projector=infra.trajectory_step_projector,
        ),
    )
    run_queries = RunQueries(
        run_repository=infra.run_repository,
        trajectory_repository=infra.trajectory_repository,
        trace_repository=infra.trace_repository,
    )
    run_commands = RunCommands(
        run_repository=infra.run_repository,
        agent_catalog=infra.runnable_agent_catalog,
        submission_service=run_submission,
    )
    run_execution_service = RunExecutionService(
        run_repository=infra.run_repository,
        published_runtime=infra.model_runtime,
        telemetry_ingestor=telemetry_ingestor,
    )

    return RunModuleBundle(
        run_submission=run_submission,
        telemetry_ingestor=telemetry_ingestor,
        run_queries=run_queries,
        run_commands=run_commands,
        run_execution_service=run_execution_service,
    )
