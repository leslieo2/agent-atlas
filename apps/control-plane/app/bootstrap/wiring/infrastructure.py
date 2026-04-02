from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit, urlunsplit

from app.agent_tracing.adapters import TraceIngestProjector
from app.agent_tracing.backends import (
    PhoenixTraceLinkResolver,
    StateTraceBackend,
)
from app.agent_tracing.exporters import NoopTraceExporter, OtlpTraceExporter
from app.core.config import RuntimeMode, settings
from app.data_plane.adapters import TraceEventTrajectoryProjector
from app.execution.adapters import (
    DockerContainerRunner,
    ExecutionControlRegistry,
    ExternalRunnerExecutionAdapter,
    K8sContainerRunner,
    K8sJobExecutionAdapter,
    K8sLauncher,
    KubectlK8sClient,
    LocalLauncher,
    LocalProcessRunner,
    LocalWorkerExecutionAdapter,
    PublishedArtifactResolver,
    RunnerRegistry,
)
from app.execution.adapters.control import _ExecutionBackendAdapter
from app.execution.adapters.runner import _RunnerExecutor
from app.execution.application.ports import (
    ArtifactResolverPort,
    ExecutionControlPort,
    RunnerPort,
)
from app.infrastructure.adapters.agent_catalog import (
    FilesystemAgentDiscovery,
    FilesystemAgentSourceCatalog,
    StateLiveAgentDiscovery,
    StatePublishedAgentCatalog,
)
from app.infrastructure.adapters.framework_registry import (
    FrameworkRegistry,
    PublishedAgentExecutionDispatcher,
    discover_framework_plugins,
)
from app.infrastructure.adapters.runtime import ModelRuntimeService
from app.infrastructure.adapters.task_queue import StateTaskQueue
from app.infrastructure.repositories import (
    StateApprovalPolicyRepository,
    StateLiveAgentMarkerRepository,
    StatePublishedAgentRepository,
    StateSystemStatus,
)
from app.modules.agents.application.ports import (
    FrameworkRegistryPort,
    PublishedAgentCatalogPort,
    PublishedAgentExecutionPort,
)
from app.modules.datasets.adapters.outbound.persistence.state import StateDatasetRepository
from app.modules.experiments.adapters.outbound.persistence.state import (
    StateExperimentRepository,
    StateRunEvaluationRepository,
)
from app.modules.exports.adapters.outbound.persistence.state import StateExportRepository
from app.modules.runs.adapters.outbound.persistence.state import (
    StateRunRepository,
    StateTraceRepository,
    StateTrajectoryRepository,
)
from app.modules.runs.application.ports import TraceBackendPort, TraceExporterPort
from app.modules.shared.domain.constants import EXTERNAL_RUNNER_EXECUTION_BACKEND


@dataclass(frozen=True)
class TracingInfrastructure:
    trace_repository: StateTraceRepository
    trajectory_repository: StateTrajectoryRepository
    trace_backend: TraceBackendPort
    trace_exporter: TraceExporterPort
    trace_projector: TraceIngestProjector
    trajectory_step_projector: TraceEventTrajectoryProjector


@dataclass(frozen=True)
class ExecutionInfrastructure:
    task_queue: StateTaskQueue
    model_runtime: ModelRuntimeService
    artifact_resolver: ArtifactResolverPort
    runner: RunnerPort
    execution_control: ExecutionControlPort
    default_runner_backend: str


@dataclass(frozen=True)
class InfrastructureBundle:
    run_repository: StateRunRepository
    dataset_repository: StateDatasetRepository
    experiment_repository: StateExperimentRepository
    run_evaluation_repository: StateRunEvaluationRepository
    export_repository: StateExportRepository
    published_agent_repository: StatePublishedAgentRepository
    live_agent_marker_repository: StateLiveAgentMarkerRepository
    approval_policy_repository: StateApprovalPolicyRepository
    system_status: StateSystemStatus
    agent_source_catalog: FilesystemAgentSourceCatalog
    framework_registry: FrameworkRegistryPort
    published_execution_dispatcher: PublishedAgentExecutionPort
    agent_discovery: FilesystemAgentDiscovery
    live_agent_discovery: StateLiveAgentDiscovery
    published_agent_catalog: PublishedAgentCatalogPort
    tracing: TracingInfrastructure
    execution: ExecutionInfrastructure


def _default_phoenix_otlp_endpoint(base_url: str | None) -> str | None:
    if not isinstance(base_url, str):
        return None
    normalized = base_url.strip()
    if not normalized:
        return None
    split = urlsplit(normalized)
    if not split.scheme or not split.netloc:
        return None
    base_path = split.path.rstrip("/")
    trace_path = f"{base_path}/v1/traces" if base_path else "/v1/traces"
    return urlunsplit((split.scheme, split.netloc, trace_path, "", ""))


def build_infrastructure() -> InfrastructureBundle:
    run_repository = StateRunRepository()
    trajectory_repository = StateTrajectoryRepository()
    trace_repository = StateTraceRepository()
    dataset_repository = StateDatasetRepository()
    experiment_repository = StateExperimentRepository()
    run_evaluation_repository = StateRunEvaluationRepository()
    export_repository = StateExportRepository()
    published_agent_repository = StatePublishedAgentRepository()
    live_agent_marker_repository = StateLiveAgentMarkerRepository()
    approval_policy_repository = StateApprovalPolicyRepository()
    system_status = StateSystemStatus()
    agent_source_catalog = FilesystemAgentSourceCatalog()
    framework_plugins = discover_framework_plugins()
    framework_registry = FrameworkRegistry(plugins=framework_plugins)
    published_execution_dispatcher = PublishedAgentExecutionDispatcher(plugins=framework_plugins)
    agent_discovery = FilesystemAgentDiscovery(
        source_catalog=agent_source_catalog,
        validator=framework_registry,
    )
    live_agent_discovery = StateLiveAgentDiscovery(markers=live_agent_marker_repository)
    task_queue = StateTaskQueue()
    effective_runtime_mode = settings.effective_runtime_mode()
    published_agent_catalog: PublishedAgentCatalogPort
    if effective_runtime_mode == RuntimeMode.LIVE:
        published_agent_catalog = published_agent_repository
    else:
        published_agent_catalog = StatePublishedAgentCatalog(
            published_agents=published_agent_repository,
            discovery=agent_discovery,
        )
    model_runtime = ModelRuntimeService(
        published_execution_dispatcher=published_execution_dispatcher,
    )
    artifact_resolver = PublishedArtifactResolver()
    k8s_launcher = K8sLauncher(
        namespace=settings.k8s_namespace,
        service_account_name=settings.k8s_service_account_name,
    )
    k8s_runner = K8sContainerRunner(
        run_repository=run_repository,
        launcher=k8s_launcher,
        client=KubectlK8sClient(command=settings.k8s_kubectl_command),
        poll_interval_seconds=settings.k8s_poll_interval_seconds,
        heartbeat_interval_seconds=settings.k8s_heartbeat_interval_seconds,
    )
    docker_runner = DockerContainerRunner(launcher=LocalLauncher())
    runners: dict[str, _RunnerExecutor] = {
        docker_runner.backend_name(): docker_runner,
        k8s_runner.backend_name(): k8s_runner,
    }
    execution_backends: dict[str, _ExecutionBackendAdapter] = {
        EXTERNAL_RUNNER_EXECUTION_BACKEND: ExternalRunnerExecutionAdapter(
            task_queue=task_queue,
            run_repository=run_repository,
        ),
        "k8s-job": K8sJobExecutionAdapter(
            task_queue=task_queue,
            run_repository=run_repository,
            launcher=k8s_launcher,
        ),
    }
    default_runner_backend = k8s_runner.backend_name()
    if effective_runtime_mode != RuntimeMode.LIVE:
        local_process_runner = LocalProcessRunner(
            published_runtime=model_runtime,
            launcher=LocalLauncher(),
        )
        runners[local_process_runner.backend_name()] = local_process_runner
        execution_backends["local-runner"] = LocalWorkerExecutionAdapter(
            task_queue=task_queue,
            run_repository=run_repository,
        )
        default_runner_backend = local_process_runner.backend_name()
    runner = RunnerRegistry(runners=runners)
    execution_control = ExecutionControlRegistry(backends=execution_backends)
    trace_backend: TraceBackendPort
    trace_exporter: TraceExporterPort
    trace_link_resolver = None
    phoenix_api_key = (
        settings.phoenix_api_key.get_secret_value() if settings.phoenix_api_key else None
    )
    tracing_otlp_endpoint = settings.tracing_otlp_endpoint or _default_phoenix_otlp_endpoint(
        settings.phoenix_base_url
    )
    trace_backend = StateTraceBackend(
        repository=trace_repository,
        backend_name="state",
    )
    if settings.phoenix_base_url:
        trace_link_resolver = PhoenixTraceLinkResolver(
            base_url=settings.phoenix_base_url,
            project_name=settings.tracing_project_name,
            api_key=phoenix_api_key,
        )

    tracing_headers = dict(settings.tracing_headers)
    if (
        settings.phoenix_base_url
        and phoenix_api_key is not None
        and "api_key" not in tracing_headers
    ):
        tracing_headers["api_key"] = phoenix_api_key

    if tracing_otlp_endpoint:
        trace_reference_backend = (
            "phoenix" if trace_link_resolver is not None else trace_backend.backend_name()
        )
        trace_exporter = OtlpTraceExporter(
            endpoint=tracing_otlp_endpoint,
            project_name=settings.tracing_project_name,
            backend_name=trace_reference_backend,
            headers=tracing_headers,
            timeout=settings.tracing_otlp_timeout_seconds,
            link_resolver=trace_link_resolver,
        )
    else:
        trace_exporter = NoopTraceExporter()
    trace_projector = TraceIngestProjector()
    trajectory_step_projector = TraceEventTrajectoryProjector()

    tracing = TracingInfrastructure(
        trace_repository=trace_repository,
        trajectory_repository=trajectory_repository,
        trace_backend=trace_backend,
        trace_exporter=trace_exporter,
        trace_projector=trace_projector,
        trajectory_step_projector=trajectory_step_projector,
    )
    execution = ExecutionInfrastructure(
        task_queue=task_queue,
        model_runtime=model_runtime,
        artifact_resolver=artifact_resolver,
        runner=runner,
        execution_control=execution_control,
        default_runner_backend=default_runner_backend,
    )

    return InfrastructureBundle(
        run_repository=run_repository,
        dataset_repository=dataset_repository,
        experiment_repository=experiment_repository,
        run_evaluation_repository=run_evaluation_repository,
        export_repository=export_repository,
        published_agent_repository=published_agent_repository,
        live_agent_marker_repository=live_agent_marker_repository,
        approval_policy_repository=approval_policy_repository,
        system_status=system_status,
        agent_source_catalog=agent_source_catalog,
        framework_registry=framework_registry,
        published_execution_dispatcher=published_execution_dispatcher,
        agent_discovery=agent_discovery,
        live_agent_discovery=live_agent_discovery,
        published_agent_catalog=published_agent_catalog,
        tracing=tracing,
        execution=execution,
    )
