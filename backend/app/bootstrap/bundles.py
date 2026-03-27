from __future__ import annotations

from dataclasses import dataclass

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
from app.modules.agents.application.use_cases import (
    AgentCatalogQueries,
    AgentDiscoveryQueries,
    AgentPublicationCommands,
)
from app.modules.artifacts.application.use_cases import ArtifactCommands, ArtifactQueries
from app.modules.datasets.application.use_cases import DatasetCommands, DatasetQueries
from app.modules.evals.application.execution import (
    EvalAggregationService,
    EvalExecutionService,
)
from app.modules.evals.application.use_cases import EvalJobCommands, EvalJobQueries
from app.modules.health.application.use_cases import HealthQueries
from app.modules.runs.application.execution import RunExecutionService
from app.modules.runs.application.services import RunSubmissionService
from app.modules.runs.application.telemetry import RunTelemetryIngestionService
from app.modules.runs.application.use_cases import RunCommands, RunQueries
from app.modules.traces.application.use_cases import (
    TraceCommands,
    TraceIngestionWorkflow,
)


@dataclass(frozen=True)
class InfrastructureBundle:
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


@dataclass(frozen=True)
class AgentModuleBundle:
    agent_lookup: RunnableAgentLookupAdapter
    agent_catalog_queries: AgentCatalogQueries
    agent_discovery_queries: AgentDiscoveryQueries
    agent_publication_commands: AgentPublicationCommands


@dataclass(frozen=True)
class TraceModuleBundle:
    trace_workflow: TraceIngestionWorkflow
    trace_commands: TraceCommands


@dataclass(frozen=True)
class DatasetModuleBundle:
    dataset_queries: DatasetQueries
    dataset_commands: DatasetCommands


@dataclass(frozen=True)
class RunModuleBundle:
    run_submission: RunSubmissionService
    telemetry_ingestor: RunTelemetryIngestionService
    run_queries: RunQueries
    run_commands: RunCommands
    run_execution_service: RunExecutionService


@dataclass(frozen=True)
class EvalModuleBundle:
    eval_run_gateway: StateEvalRunGateway
    eval_queries: EvalJobQueries
    eval_commands: EvalJobCommands
    eval_execution_service: EvalExecutionService
    eval_aggregation_service: EvalAggregationService


@dataclass(frozen=True)
class ArtifactModuleBundle:
    artifact_exporter: ArtifactExporterAdapter
    artifact_queries: ArtifactQueries
    artifact_commands: ArtifactCommands


@dataclass(frozen=True)
class HealthModuleBundle:
    health_queries: HealthQueries


@dataclass(frozen=True)
class WorkerBundle:
    app_worker: AppWorker
