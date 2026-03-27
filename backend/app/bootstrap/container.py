from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING

from app.bootstrap.wiring.agents import build_agent_module
from app.bootstrap.wiring.artifacts import build_artifact_module
from app.bootstrap.wiring.datasets import build_dataset_module
from app.bootstrap.wiring.evals import build_eval_module
from app.bootstrap.wiring.health import build_health_module
from app.bootstrap.wiring.infrastructure import build_infrastructure
from app.bootstrap.wiring.runs import build_run_module
from app.bootstrap.wiring.traces import build_trace_module
from app.bootstrap.wiring.worker import build_worker_bundle
from app.modules.agents.application.use_cases import (
    AgentCatalogQueries,
    AgentDiscoveryQueries,
    AgentPublicationCommands,
)
from app.modules.artifacts.application.use_cases import ArtifactCommands, ArtifactQueries
from app.modules.datasets.application.use_cases import DatasetCommands, DatasetQueries
from app.modules.evals.application.use_cases import EvalJobCommands, EvalJobQueries
from app.modules.health.application.use_cases import HealthQueries
from app.modules.runs.application.telemetry import RunTelemetryIngestionService
from app.modules.runs.application.use_cases import RunCommands, RunQueries
from app.modules.traces.application.use_cases import TraceCommands

if TYPE_CHECKING:
    from app.bootstrap.worker import AppWorker
    from app.infrastructure.adapters.agent_catalog import (
        FilesystemAgentDiscovery,
        FilesystemAgentSourceCatalog,
        StateRunnableAgentCatalog,
    )
    from app.infrastructure.adapters.artifacts import ArtifactExporterAdapter
    from app.infrastructure.adapters.evals import RunnableAgentLookupAdapter, StateEvalRunGateway
    from app.infrastructure.adapters.openai_agents import (
        OpenAIAgentContractValidator,
        PublishedOpenAIAgentLoader,
    )
    from app.infrastructure.adapters.runtime import ModelRuntimeService
    from app.infrastructure.adapters.task_queue import StateTaskQueue
    from app.infrastructure.adapters.trace_projection import TraceIngestProjector
    from app.infrastructure.adapters.trajectory_projection import TraceEventTrajectoryProjector
    from app.infrastructure.repositories import (
        StateArtifactRepository,
        StateDatasetRepository,
        StateEvalJobRepository,
        StateEvalSampleResultRepository,
        StatePublishedAgentRepository,
        StateRunRepository,
        StateSystemStatus,
        StateTraceRepository,
        StateTrajectoryRepository,
    )
    from app.modules.datasets.application.use_cases import DatasetCommands, DatasetQueries
    from app.modules.evals.application.execution import (
        EvalAggregationService,
        EvalExecutionService,
    )
    from app.modules.runs.application.execution import RunExecutionService
    from app.modules.runs.application.services import RunSubmissionService
    from app.modules.traces.application.use_cases import (
        TraceIngestionWorkflow,
    )


def _bind_bundle(target: object, bundle: object) -> None:
    for name, value in vars(bundle).items():
        setattr(target, name, value)


class AppContainer:
    run_repository: StateRunRepository
    trajectory_repository: StateTrajectoryRepository
    trace_repository: StateTraceRepository
    dataset_repository: StateDatasetRepository
    eval_job_repository: StateEvalJobRepository
    eval_sample_result_repository: StateEvalSampleResultRepository
    artifact_repository: StateArtifactRepository
    published_agent_repository: StatePublishedAgentRepository
    system_status: StateSystemStatus
    agent_source_catalog: FilesystemAgentSourceCatalog
    agent_validator: OpenAIAgentContractValidator
    agent_discovery: FilesystemAgentDiscovery
    runnable_agent_catalog: StateRunnableAgentCatalog
    task_queue: StateTaskQueue
    published_agent_loader: PublishedOpenAIAgentLoader
    model_runtime: ModelRuntimeService
    trace_projector: TraceIngestProjector
    trajectory_step_projector: TraceEventTrajectoryProjector
    agent_lookup: RunnableAgentLookupAdapter
    agent_catalog_queries: AgentCatalogQueries
    agent_discovery_queries: AgentDiscoveryQueries
    agent_publication_commands: AgentPublicationCommands
    trace_workflow: TraceIngestionWorkflow
    trace_commands: TraceCommands
    dataset_queries: DatasetQueries
    dataset_commands: DatasetCommands
    run_submission: RunSubmissionService
    telemetry_ingestor: RunTelemetryIngestionService
    run_queries: RunQueries
    run_commands: RunCommands
    run_execution_service: RunExecutionService
    eval_run_gateway: StateEvalRunGateway
    eval_queries: EvalJobQueries
    eval_commands: EvalJobCommands
    eval_execution_service: EvalExecutionService
    eval_aggregation_service: EvalAggregationService
    artifact_exporter: ArtifactExporterAdapter
    artifact_queries: ArtifactQueries
    artifact_commands: ArtifactCommands
    health_queries: HealthQueries
    app_worker: AppWorker

    def __init__(self) -> None:
        infrastructure = build_infrastructure()
        _bind_bundle(self, infrastructure)

        agents = build_agent_module(infrastructure)
        _bind_bundle(self, agents)

        traces = build_trace_module(infrastructure)
        _bind_bundle(self, traces)

        datasets = build_dataset_module(infrastructure)
        _bind_bundle(self, datasets)

        runs = build_run_module(infrastructure, traces)
        _bind_bundle(self, runs)

        evals = build_eval_module(infrastructure, agents, runs)
        _bind_bundle(self, evals)

        artifacts = build_artifact_module(infrastructure)
        _bind_bundle(self, artifacts)

        health = build_health_module(infrastructure)
        _bind_bundle(self, health)

        worker = build_worker_bundle(infrastructure, runs, evals)
        _bind_bundle(self, worker)


@lru_cache
def get_container() -> AppContainer:
    return AppContainer()


def get_run_queries() -> RunQueries:
    return get_container().run_queries


def get_run_commands() -> RunCommands:
    return get_container().run_commands


def get_dataset_queries() -> DatasetQueries:
    return get_container().dataset_queries


def get_dataset_commands() -> DatasetCommands:
    return get_container().dataset_commands


def get_eval_queries() -> EvalJobQueries:
    return get_container().eval_queries


def get_eval_commands() -> EvalJobCommands:
    return get_container().eval_commands


def get_artifact_queries() -> ArtifactQueries:
    return get_container().artifact_queries


def get_artifact_commands() -> ArtifactCommands:
    return get_container().artifact_commands


def get_agent_catalog_queries() -> AgentCatalogQueries:
    return get_container().agent_catalog_queries


def get_agent_discovery_queries() -> AgentDiscoveryQueries:
    return get_container().agent_discovery_queries


def get_agent_publication_commands() -> AgentPublicationCommands:
    return get_container().agent_publication_commands


def get_trace_commands() -> TraceCommands:
    return get_container().trace_commands


def get_run_telemetry_ingestor() -> RunTelemetryIngestionService:
    return get_container().telemetry_ingestor


def get_health_queries() -> HealthQueries:
    return get_container().health_queries
