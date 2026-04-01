from __future__ import annotations

from dataclasses import dataclass

from app.agent_tracing.application import (
    RunObservationService,
    RunTraceMetadataRecorder,
    TraceExportCoordinator,
    TraceSpanRecorder,
    TrajectoryRecorder,
)
from app.bootstrap.wiring.infrastructure import InfrastructureBundle
from app.core.config import settings
from app.execution.application import RunExecutionService
from app.modules.runs.adapters.outbound.execution.state_sink import RunExecutionStateSink
from app.modules.runs.adapters.outbound.telemetry import RunTracingStateRecorder
from app.modules.runs.application.services import RunSubmissionService
from app.modules.runs.application.use_cases import RunCommands, RunQueries
from app.modules.shared.application.contracts import RunObservationSinkPort


@dataclass(frozen=True)
class RunModuleBundle:
    run_submission: RunSubmissionService
    telemetry_ingestor: RunObservationSinkPort
    run_queries: RunQueries
    run_commands: RunCommands
    run_execution_service: RunExecutionService


def build_run_module(
    infra: InfrastructureBundle,
) -> RunModuleBundle:
    run_submission = RunSubmissionService(
        run_repository=infra.run_repository,
        execution_control=infra.execution.execution_control,
        default_trace_backend=infra.tracing.trace_backend.backend_name(),
        default_k8s_runner_image=settings.k8s_default_runner_image,
    )
    telemetry_ingestor = RunObservationService(
        trace_span_recorder=TraceSpanRecorder(
            trace_repository=infra.tracing.trace_repository,
            trace_projector=infra.tracing.trace_projector,
        ),
        trajectory_recorder=TrajectoryRecorder(
            trajectory_repository=infra.tracing.trajectory_repository,
            step_projector=infra.tracing.trajectory_step_projector,
        ),
        trace_export_coordinator=TraceExportCoordinator(
            trace_exporter=infra.tracing.trace_exporter,
            trace_metadata_recorder=RunTraceMetadataRecorder(
                run_tracing_state=RunTracingStateRecorder(
                    run_repository=infra.run_repository,
                ),
            ),
        ),
    )
    run_queries = RunQueries(
        run_repository=infra.run_repository,
    )
    run_commands = RunCommands(
        run_repository=infra.run_repository,
        agent_catalog=infra.published_agent_catalog,
        submission_service=run_submission,
        execution_control=infra.execution.execution_control,
    )
    run_execution_service = RunExecutionService(
        artifact_resolver=infra.execution.artifact_resolver,
        runner=infra.execution.runner,
        sink=RunExecutionStateSink(
            run_repository=infra.run_repository,
            observation_sink=telemetry_ingestor,
        ),
        default_runner_backend=infra.execution.default_runner_backend,
    )

    return RunModuleBundle(
        run_submission=run_submission,
        telemetry_ingestor=telemetry_ingestor,
        run_queries=run_queries,
        run_commands=run_commands,
        run_execution_service=run_execution_service,
    )
