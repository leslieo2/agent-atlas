from __future__ import annotations

from dataclasses import dataclass

from app.core.config import TraceBackendMode, settings
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
from app.infrastructure.adapters.observability import (
    NoopTraceExporter,
    OtlpTraceExporter,
    StateTraceBackend,
)
from app.infrastructure.adapters.openai_agents import (
    OpenAIAgentContractValidator,
    PublishedOpenAIAgentAdapter,
    PublishedOpenAIAgentLoader,
)
from app.infrastructure.adapters.phoenix import PhoenixTraceBackend
from app.infrastructure.adapters.runtime import ModelRuntimeService
from app.infrastructure.adapters.task_queue import StateTaskQueue
from app.infrastructure.repositories import (
    StateApprovalPolicyRepository,
    StatePublishedAgentRepository,
    StateSystemStatus,
)
from app.modules.agents.application.ports import ArtifactBuilderPort, FrameworkRegistryPort
from app.modules.datasets.adapters.outbound.persistence import StateDatasetRepository
from app.modules.execution.application.ports import ExecutionControlPort
from app.modules.experiments.adapters.outbound.persistence import (
    StateExperimentRepository,
    StateRunEvaluationRepository,
)
from app.modules.exports.adapters.outbound.persistence import StateExportRepository
from app.modules.runs.adapters.outbound.execution import (
    ExecutionControlRegistry,
    K8sJobExecutionAdapter,
    K8sLauncher,
    LocalLauncher,
    LocalProcessRunner,
    LocalWorkerExecutionAdapter,
    PublishedArtifactResolver,
    RunnerRegistry,
)
from app.modules.runs.adapters.outbound.persistence import (
    StateRunRepository,
    StateTraceRepository,
    StateTrajectoryRepository,
)
from app.modules.runs.adapters.outbound.telemetry.trace_projector import TraceIngestProjector
from app.modules.runs.adapters.outbound.telemetry.trajectory_projector import (
    TraceEventTrajectoryProjector,
)
from app.modules.runs.application.ports import (
    ArtifactResolverPort,
    RunnerPort,
    TraceBackendPort,
    TraceExporterPort,
)


@dataclass(frozen=True)
class InfrastructureBundle:
    run_repository: StateRunRepository
    trajectory_repository: StateTrajectoryRepository
    trace_repository: StateTraceRepository
    dataset_repository: StateDatasetRepository
    experiment_repository: StateExperimentRepository
    run_evaluation_repository: StateRunEvaluationRepository
    export_repository: StateExportRepository
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
    export_repository = StateExportRepository()
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
    artifact_builder = SourceArtifactBuilder(default_trace_backend=settings.trace_backend.value)
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
        launcher=LocalLauncher(),
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
                launcher=K8sLauncher(),
            ),
            "local-runner": LocalWorkerExecutionAdapter(
                task_queue=task_queue,
                run_repository=run_repository,
            ),
        }
    )
    trace_backend: TraceBackendPort
    trace_exporter: TraceExporterPort
    phoenix_api_key = (
        settings.phoenix_api_key.get_secret_value() if settings.phoenix_api_key else None
    )
    if settings.trace_backend == TraceBackendMode.PHOENIX:
        if not settings.phoenix_base_url:
            raise RuntimeError("Phoenix trace queries require AGENT_ATLAS_PHOENIX_BASE_URL.")
        trace_backend = PhoenixTraceBackend(
            run_repository=run_repository,
            base_url=settings.phoenix_base_url,
            project_name=settings.observability_project_name,
            api_key=phoenix_api_key,
            query_limit=settings.phoenix_query_limit,
        )
    else:
        trace_backend = StateTraceBackend(
            repository=trace_repository,
            backend_name=settings.trace_backend.value,
        )

    observability_headers = dict(settings.observability_headers)
    if (
        settings.trace_backend == TraceBackendMode.PHOENIX
        and phoenix_api_key is not None
        and "api_key" not in observability_headers
    ):
        observability_headers["api_key"] = phoenix_api_key

    if settings.observability_otlp_endpoint:
        trace_exporter = OtlpTraceExporter(
            endpoint=settings.observability_otlp_endpoint,
            project_name=settings.observability_project_name,
            backend_name=trace_backend.backend_name(),
            base_url=settings.phoenix_base_url
            if settings.trace_backend == TraceBackendMode.PHOENIX
            else None,
            headers=observability_headers,
            api_key=phoenix_api_key,
        )
    else:
        trace_exporter = NoopTraceExporter()
    trace_projector = TraceIngestProjector()
    trajectory_step_projector = TraceEventTrajectoryProjector()

    return InfrastructureBundle(
        run_repository=run_repository,
        trajectory_repository=trajectory_repository,
        trace_repository=trace_repository,
        dataset_repository=dataset_repository,
        experiment_repository=experiment_repository,
        run_evaluation_repository=run_evaluation_repository,
        export_repository=export_repository,
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
