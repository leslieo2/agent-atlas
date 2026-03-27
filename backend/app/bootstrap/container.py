from __future__ import annotations

from functools import lru_cache

from app.bootstrap.worker import AppWorker
from app.infrastructure.adapters.agents import (
    FilesystemAgentDiscovery,
    FilesystemAgentSourceCatalog,
    OpenAIAgentContractValidator,
    PublishedOpenAIAgentLoader,
    StateRunnableAgentCatalog,
)
from app.infrastructure.adapters.artifacts import ArtifactExporterAdapter
from app.infrastructure.adapters.evals import RunnableAgentLookupAdapter, StateEvalRunGateway
from app.infrastructure.adapters.model_runtime import (
    ModelRuntimeService,
    PublishedOpenAIAgentAdapter,
)
from app.infrastructure.adapters.runner import (
    FallbackRunnerAdapter,
    StaticRunnerRegistry,
)
from app.infrastructure.adapters.tasks import StateTaskQueue
from app.infrastructure.adapters.traces import DefaultTraceProjector
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
from app.modules.runs.application.use_cases import RunCommands, RunQueries
from app.modules.traces.application.use_cases import (
    TraceCommands,
    TraceIngestionWorkflow,
    TraceRecorder,
)


class AppContainer:
    def __init__(self) -> None:
        self.run_repository = StateRunRepository()
        self.trajectory_repository = StateTrajectoryRepository()
        self.trace_repository = StateTraceRepository()
        self.dataset_repository = StateDatasetRepository()
        self.eval_job_repository = StateEvalJobRepository()
        self.eval_sample_result_repository = StateEvalSampleResultRepository()
        self.artifact_repository = StateArtifactRepository()
        self.agent_source_catalog = FilesystemAgentSourceCatalog()
        self.agent_validator = OpenAIAgentContractValidator()
        self.agent_discovery = FilesystemAgentDiscovery(
            source_catalog=self.agent_source_catalog,
            validator=self.agent_validator,
        )
        self.published_agent_repository = StatePublishedAgentRepository()
        self.runnable_agent_catalog = StateRunnableAgentCatalog(
            discovery=self.agent_discovery,
            published_agents=self.published_agent_repository,
        )
        self.system_status = StateSystemStatus()
        self.task_queue = StateTaskQueue()
        self.published_agent_loader = PublishedOpenAIAgentLoader(validator=self.agent_validator)
        self.model_runtime = ModelRuntimeService(
            published_adapter=PublishedOpenAIAgentAdapter(agent_loader=self.published_agent_loader)
        )
        self.runner = FallbackRunnerAdapter(runtime_service=self.model_runtime)
        self.runner_registry = StaticRunnerRegistry(default_runner=self.runner)
        self.trace_projector = DefaultTraceProjector()
        self.trace_workflow = TraceIngestionWorkflow(
            trace_projector=self.trace_projector,
            trace_recorder=TraceRecorder(
                trace_repository=self.trace_repository,
                trajectory_repository=self.trajectory_repository,
            ),
        )
        self.trace_commands = TraceCommands(workflow=self.trace_workflow)
        self.agent_lookup = RunnableAgentLookupAdapter(agent_catalog=self.runnable_agent_catalog)
        self.eval_run_gateway = StateEvalRunGateway(
            run_repository=self.run_repository,
            trajectory_repository=self.trajectory_repository,
            task_queue=self.task_queue,
            agent_catalog=self.runnable_agent_catalog,
        )
        self.artifact_exporter = ArtifactExporterAdapter(
            trajectory_repository=self.trajectory_repository,
            artifact_repository=self.artifact_repository,
            run_repository=self.run_repository,
        )

        run_execution_service = RunExecutionService(
            run_repository=self.run_repository,
            published_runtime=self.model_runtime,
            trace_ingestor=self.trace_commands,
        )

        self.run_queries = RunQueries(
            run_repository=self.run_repository,
            trajectory_repository=self.trajectory_repository,
            trace_repository=self.trace_repository,
        )
        self.run_commands = RunCommands(
            run_repository=self.run_repository,
            task_queue=self.task_queue,
            agent_catalog=self.runnable_agent_catalog,
        )
        self.dataset_queries = DatasetQueries(dataset_repository=self.dataset_repository)
        self.dataset_commands = DatasetCommands(dataset_repository=self.dataset_repository)
        self.eval_queries = EvalJobQueries(
            eval_job_repository=self.eval_job_repository,
            sample_result_repository=self.eval_sample_result_repository,
        )
        self.eval_commands = EvalJobCommands(
            eval_job_repository=self.eval_job_repository,
            dataset_source=self.dataset_repository,
            agent_lookup=self.agent_lookup,
            task_queue=self.task_queue,
        )
        self.eval_execution_service = EvalExecutionService(
            eval_job_repository=self.eval_job_repository,
            dataset_source=self.dataset_repository,
            eval_run_gateway=self.eval_run_gateway,
            task_queue=self.task_queue,
        )
        self.eval_aggregation_service = EvalAggregationService(
            eval_job_repository=self.eval_job_repository,
            sample_result_repository=self.eval_sample_result_repository,
            dataset_source=self.dataset_repository,
            eval_run_gateway=self.eval_run_gateway,
            task_queue=self.task_queue,
        )
        self.artifact_queries = ArtifactQueries(artifact_repository=self.artifact_repository)
        self.artifact_commands = ArtifactCommands(artifact_exporter=self.artifact_exporter)
        self.agent_catalog_queries = AgentCatalogQueries(
            runnable_catalog=self.runnable_agent_catalog
        )
        self.agent_discovery_queries = AgentDiscoveryQueries(
            discovery=self.agent_discovery,
            published_agents=self.published_agent_repository,
        )
        self.agent_publication_commands = AgentPublicationCommands(
            discovery=self.agent_discovery,
            published_agents=self.published_agent_repository,
        )
        self.health_queries = HealthQueries(system_status=self.system_status)
        self.app_worker = AppWorker(
            task_queue=self.task_queue,
            run_execution_service=run_execution_service,
            eval_execution_service=self.eval_execution_service,
            eval_aggregation_service=self.eval_aggregation_service,
        )


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


def get_health_queries() -> HealthQueries:
    return get_container().health_queries
