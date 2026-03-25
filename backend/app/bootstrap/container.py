from __future__ import annotations

from functools import lru_cache

from app.bootstrap.worker import AppWorker
from app.infrastructure.adapters.artifacts import ArtifactExporterAdapter
from app.infrastructure.adapters.runner import (
    FallbackRunnerAdapter,
    StaticRunnerRegistry,
)
from app.infrastructure.adapters.tasks import StateTaskQueue
from app.infrastructure.adapters.traces import DefaultTraceProjector
from app.infrastructure.repositories import (
    StateAdapterCatalog,
    StateArtifactRepository,
    StateDatasetRepository,
    StateEvalJobRepository,
    StateReplayRepository,
    StateRunRepository,
    StateSystemStatus,
    StateTraceRepository,
    StateTrajectoryRepository,
)
from app.modules.adapters.application.use_cases import AdapterQueries
from app.modules.artifacts.application.use_cases import ArtifactCommands, ArtifactQueries
from app.modules.datasets.application.use_cases import DatasetCommands, DatasetQueries
from app.modules.evals.application.execution import EvalJobRecorder, EvalJobRunner
from app.modules.evals.application.use_cases import EvalJobCommands, EvalJobQueries
from app.modules.health.application.use_cases import HealthQueries
from app.modules.replays.application.execution import ReplayExecutor
from app.modules.replays.application.use_cases import ReplayCommands, ReplayQueries
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
        self.replay_repository = StateReplayRepository()
        self.artifact_repository = StateArtifactRepository()
        self.adapter_catalog = StateAdapterCatalog()
        self.system_status = StateSystemStatus()
        self.task_queue = StateTaskQueue()
        self.runner = FallbackRunnerAdapter()
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
        self.artifact_exporter = ArtifactExporterAdapter(
            trajectory_repository=self.trajectory_repository,
            artifact_repository=self.artifact_repository,
        )

        run_execution_service = RunExecutionService(
            run_repository=self.run_repository,
            runner_registry=self.runner_registry,
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
        )
        self.replay_queries = ReplayQueries(replay_repository=self.replay_repository)
        self.replay_commands = ReplayCommands(
            trajectory_repository=self.trajectory_repository,
            run_repository=self.run_repository,
            replay_repository=self.replay_repository,
            replay_executor=ReplayExecutor(runner_registry=self.runner_registry),
        )
        self.eval_job_queries = EvalJobQueries(eval_job_repository=self.eval_job_repository)
        eval_job_runner = EvalJobRunner(
            recorder=EvalJobRecorder(eval_job_repository=self.eval_job_repository),
        )
        self.eval_job_commands = EvalJobCommands(
            eval_job_repository=self.eval_job_repository,
            task_queue=self.task_queue,
        )
        self.dataset_queries = DatasetQueries(dataset_repository=self.dataset_repository)
        self.dataset_commands = DatasetCommands(dataset_repository=self.dataset_repository)
        self.artifact_queries = ArtifactQueries(artifact_repository=self.artifact_repository)
        self.artifact_commands = ArtifactCommands(artifact_exporter=self.artifact_exporter)
        self.adapter_queries = AdapterQueries(adapter_catalog=self.adapter_catalog)
        self.health_queries = HealthQueries(system_status=self.system_status)
        self.app_worker = AppWorker(
            task_queue=self.task_queue,
            run_execution_service=run_execution_service,
            eval_job_runner=eval_job_runner,
        )


@lru_cache
def get_container() -> AppContainer:
    return AppContainer()


def get_run_queries() -> RunQueries:
    return get_container().run_queries


def get_run_commands() -> RunCommands:
    return get_container().run_commands


def get_replay_queries() -> ReplayQueries:
    return get_container().replay_queries


def get_replay_commands() -> ReplayCommands:
    return get_container().replay_commands


def get_eval_job_queries() -> EvalJobQueries:
    return get_container().eval_job_queries


def get_eval_job_commands() -> EvalJobCommands:
    return get_container().eval_job_commands


def get_dataset_queries() -> DatasetQueries:
    return get_container().dataset_queries


def get_dataset_commands() -> DatasetCommands:
    return get_container().dataset_commands


def get_artifact_queries() -> ArtifactQueries:
    return get_container().artifact_queries


def get_artifact_commands() -> ArtifactCommands:
    return get_container().artifact_commands


def get_trace_commands() -> TraceCommands:
    return get_container().trace_commands


def get_adapter_queries() -> AdapterQueries:
    return get_container().adapter_queries


def get_health_queries() -> HealthQueries:
    return get_container().health_queries
