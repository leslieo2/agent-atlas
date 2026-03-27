from __future__ import annotations

from app.bootstrap.bundles import InfrastructureBundle
from app.infrastructure.adapters.agent_catalog import (
    FilesystemAgentDiscovery,
    FilesystemAgentSourceCatalog,
    StateRunnableAgentCatalog,
)
from app.infrastructure.adapters.openai_agents import (
    OpenAIAgentContractValidator,
    PublishedOpenAIAgentAdapter,
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
    agent_validator = OpenAIAgentContractValidator()
    agent_discovery = FilesystemAgentDiscovery(
        source_catalog=agent_source_catalog,
        validator=agent_validator,
    )
    runnable_agent_catalog = StateRunnableAgentCatalog(
        discovery=agent_discovery,
        published_agents=published_agent_repository,
    )
    task_queue = StateTaskQueue()
    published_agent_loader = PublishedOpenAIAgentLoader(validator=agent_validator)
    model_runtime = ModelRuntimeService(
        published_adapter=PublishedOpenAIAgentAdapter(agent_loader=published_agent_loader)
    )
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
        agent_validator=agent_validator,
        agent_discovery=agent_discovery,
        runnable_agent_catalog=runnable_agent_catalog,
        task_queue=task_queue,
        published_agent_loader=published_agent_loader,
        model_runtime=model_runtime,
        trace_projector=trace_projector,
        trajectory_step_projector=trajectory_step_projector,
    )
