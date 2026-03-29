from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from app.core.config import TraceBackendMode, settings
from app.infrastructure.adapters.agent_catalog import (
    FilesystemAgentDiscovery,
    FilesystemAgentSourceCatalog,
    StateRunnableAgentCatalog,
)
from app.infrastructure.adapters.artifact_builder import SourceArtifactBuilder
from app.infrastructure.adapters.execution import (
    ExecutionControlRegistry,
    K8sJobExecutionAdapter,
    LocalWorkerExecutionAdapter,
)
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
from app.infrastructure.adapters.phoenix import (
    PhoenixTraceBackend,
    PhoenixTraceExporter,
)
from app.infrastructure.adapters.runner import (
    LocalProcessRunner,
    PublishedArtifactResolver,
    RunnerRegistry,
)
from app.infrastructure.adapters.runtime import ModelRuntimeService
from app.infrastructure.adapters.task_queue import StateTaskQueue
from app.infrastructure.adapters.trace_projection import TraceIngestProjector
from app.infrastructure.adapters.trajectory_projection import TraceEventTrajectoryProjector
from app.infrastructure.repositories import (
    StateApprovalPolicyRepository,
    StateArtifactRepository,
    StateDatasetRepository,
    StateExperimentRepository,
    StatePublishedAgentRepository,
    StateRunEvaluationRepository,
    StateRunRepository,
    StateSystemStatus,
    StateTraceRepository,
    StateTrajectoryRepository,
)
from app.modules.agents.application.ports import ArtifactBuilderPort, FrameworkRegistryPort
from app.modules.execution.application.ports import ExecutionControlPort
from app.modules.runs.application.ports import ArtifactResolverPort, RunnerPort
from app.modules.traces.application.ports import TraceBackendPort, TraceExporterPort


def _require_phoenix_configuration() -> tuple[str, str]:
    missing: list[str] = []
    if not settings.phoenix_base_url:
        missing.append("AGENT_ATLAS_PHOENIX_BASE_URL")
    if not settings.phoenix_otlp_endpoint:
        missing.append("AGENT_ATLAS_PHOENIX_OTLP_ENDPOINT")
    if missing:
        missing_fields = ", ".join(missing)
        raise RuntimeError(
            "Phoenix-backed raw tracing is required. Configure "
            f"{missing_fields} before starting Agent Atlas."
        )
    return (
        cast("str", settings.phoenix_base_url),
        cast("str", settings.phoenix_otlp_endpoint),
    )


@dataclass(frozen=True)
class InfrastructureBundle:
    run_repository: StateRunRepository
    trajectory_repository: StateTrajectoryRepository
    trace_repository: StateTraceRepository
    dataset_repository: StateDatasetRepository
    experiment_repository: StateExperimentRepository
    run_evaluation_repository: StateRunEvaluationRepository
    artifact_repository: StateArtifactRepository
    published_agent_repository: StatePublishedAgentRepository
    approval_policy_repository: StateApprovalPolicyRepository
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
    execution_control: ExecutionControlPort
    default_runner_backend: str
    trace_backend: TraceBackendPort
    trace_exporter: TraceExporterPort
    trace_projector: TraceIngestProjector
    trajectory_step_projector: TraceEventTrajectoryProjector


def build_infrastructure() -> InfrastructureBundle:
    run_repository = StateRunRepository()
    trajectory_repository = StateTrajectoryRepository()
    trace_repository = StateTraceRepository()
    dataset_repository = StateDatasetRepository()
    experiment_repository = StateExperimentRepository()
    run_evaluation_repository = StateRunEvaluationRepository()
    artifact_repository = StateArtifactRepository()
    published_agent_repository = StatePublishedAgentRepository()
    approval_policy_repository = StateApprovalPolicyRepository()
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
    artifact_builder = SourceArtifactBuilder(default_trace_backend=TraceBackendMode.PHOENIX.value)
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
    local_process_runner = LocalProcessRunner(
        published_runtime=model_runtime,
    )
    default_runner_backend = local_process_runner.backend_name()
    runner = RunnerRegistry(
        runners={
            default_runner_backend: local_process_runner,
        },
        default_backend=default_runner_backend,
    )
    execution_control = ExecutionControlRegistry(
        backends={
            "k8s-job": K8sJobExecutionAdapter(
                task_queue=task_queue,
                run_repository=run_repository,
            ),
            "local-runner": LocalWorkerExecutionAdapter(
                task_queue=task_queue,
                run_repository=run_repository,
            ),
        }
    )
    trace_backend: TraceBackendPort
    trace_exporter: TraceExporterPort
    phoenix_base_url, phoenix_otlp_endpoint = _require_phoenix_configuration()
    phoenix_api_key = (
        settings.phoenix_api_key.get_secret_value() if settings.phoenix_api_key else None
    )
    trace_backend = PhoenixTraceBackend(
        run_repository=run_repository,
        base_url=phoenix_base_url,
        project_name=settings.phoenix_project_name,
        api_key=phoenix_api_key,
        query_limit=settings.phoenix_query_limit,
    )
    trace_exporter = PhoenixTraceExporter(
        endpoint=phoenix_otlp_endpoint,
        project_name=settings.phoenix_project_name,
        base_url=phoenix_base_url,
        api_key=phoenix_api_key,
    )
    trace_projector = TraceIngestProjector()
    trajectory_step_projector = TraceEventTrajectoryProjector()

    return InfrastructureBundle(
        run_repository=run_repository,
        trajectory_repository=trajectory_repository,
        trace_repository=trace_repository,
        dataset_repository=dataset_repository,
        experiment_repository=experiment_repository,
        run_evaluation_repository=run_evaluation_repository,
        artifact_repository=artifact_repository,
        published_agent_repository=published_agent_repository,
        approval_policy_repository=approval_policy_repository,
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
        execution_control=execution_control,
        default_runner_backend=default_runner_backend,
        trace_backend=trace_backend,
        trace_exporter=trace_exporter,
        trace_projector=trace_projector,
        trajectory_step_projector=trajectory_step_projector,
    )
