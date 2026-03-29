from __future__ import annotations

from dataclasses import dataclass

from app.infrastructure.adapters.agent_catalog import (
    FilesystemAgentDiscovery,
    FilesystemAgentSourceCatalog,
    StateRunnableAgentCatalog,
)
from app.infrastructure.adapters.artifact_builder import SourceArtifactBuilder
from app.infrastructure.adapters.framework_registry import FrameworkPlugin, FrameworkRegistry
from app.infrastructure.adapters.langchain import (
    LangChainAgentContractValidator,
    PublishedLangChainAgentAdapter,
    PublishedLangChainAgentLoader,
)
from app.infrastructure.adapters.openai_agents import (
    OpenAIAgentContractValidator,
    PublishedOpenAIAgentAdapter,
    PublishedOpenAIAgentLoader,
)
from app.infrastructure.adapters.runner import (
    LegacyPassthroughRunner,
    PublishedArtifactResolver,
)
from app.infrastructure.adapters.runtime import ModelRuntimeService
from app.infrastructure.adapters.task_queue import StateTaskQueue
from app.infrastructure.adapters.trace_backend import AtlasStateTraceBackend
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
from app.modules.agents.application.ports import ArtifactBuilderPort, FrameworkRegistryPort
from app.modules.runs.application.ports import ArtifactResolverPort, RunnerPort
from app.modules.traces.application.ports import TraceBackendPort


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
    framework_registry: FrameworkRegistryPort
    artifact_builder: ArtifactBuilderPort
    agent_discovery: FilesystemAgentDiscovery
    runnable_agent_catalog: StateRunnableAgentCatalog
    task_queue: StateTaskQueue
    model_runtime: ModelRuntimeService
    artifact_resolver: ArtifactResolverPort
    runner: RunnerPort
    trace_backend: TraceBackendPort
    trace_projector: TraceIngestProjector
    trajectory_step_projector: TraceEventTrajectoryProjector


def build_infrastructure() -> InfrastructureBundle:
    run_repository = StateRunRepository()
    trajectory_repository = StateTrajectoryRepository()
    trace_repository = StateTraceRepository()
    dataset_repository = StateDatasetRepository()
    eval_job_repository = StateEvalJobRepository()
    eval_sample_result_repository = StateEvalSampleResultRepository()
    artifact_repository = StateArtifactRepository()
    published_agent_repository = StatePublishedAgentRepository()
    system_status = StateSystemStatus()
    agent_source_catalog = FilesystemAgentSourceCatalog()
    openai_validator = OpenAIAgentContractValidator()
    openai_loader = PublishedOpenAIAgentLoader(validator=openai_validator)
    langchain_validator = LangChainAgentContractValidator()
    langchain_loader = PublishedLangChainAgentLoader(validator=langchain_validator)
    framework_registry = FrameworkRegistry(
        plugins={
            "openai-agents-sdk": FrameworkPlugin(
                framework="openai-agents-sdk",
                validator=openai_validator,
                loader=openai_loader,
                runtime=PublishedOpenAIAgentAdapter(agent_loader=openai_loader),
            ),
            "langchain": FrameworkPlugin(
                framework="langchain",
                validator=langchain_validator,
                loader=langchain_loader,
                runtime=PublishedLangChainAgentAdapter(agent_loader=langchain_loader),
            ),
        }
    )
    artifact_builder = SourceArtifactBuilder()
    agent_discovery = FilesystemAgentDiscovery(
        source_catalog=agent_source_catalog,
        validator=framework_registry,
    )
    runnable_agent_catalog = StateRunnableAgentCatalog(
        discovery=agent_discovery,
        published_agents=published_agent_repository,
    )
    task_queue = StateTaskQueue()
    model_runtime = ModelRuntimeService(
        framework_registry=framework_registry,
    )
    artifact_resolver = PublishedArtifactResolver()
    runner = LegacyPassthroughRunner(
        artifact_resolver=artifact_resolver,
        published_runtime=model_runtime,
    )
    trace_backend = AtlasStateTraceBackend(trace_repository)
    trace_projector = TraceIngestProjector()
    trajectory_step_projector = TraceEventTrajectoryProjector()

    return InfrastructureBundle(
        run_repository=run_repository,
        trajectory_repository=trajectory_repository,
        trace_repository=trace_repository,
        dataset_repository=dataset_repository,
        eval_job_repository=eval_job_repository,
        eval_sample_result_repository=eval_sample_result_repository,
        artifact_repository=artifact_repository,
        published_agent_repository=published_agent_repository,
        system_status=system_status,
        agent_source_catalog=agent_source_catalog,
        framework_registry=framework_registry,
        artifact_builder=artifact_builder,
        agent_discovery=agent_discovery,
        runnable_agent_catalog=runnable_agent_catalog,
        task_queue=task_queue,
        model_runtime=model_runtime,
        artifact_resolver=artifact_resolver,
        runner=runner,
        trace_backend=trace_backend,
        trace_projector=trace_projector,
        trajectory_step_projector=trajectory_step_projector,
    )
