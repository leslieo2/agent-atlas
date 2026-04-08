from __future__ import annotations

from uuid import UUID, uuid4

from agent_atlas_contracts.runtime import (
    AgentManifest,
)
from agent_atlas_contracts.runtime import (
    ExecutionReferenceMetadata as ExecutionReference,
)
from app.execution.application.experiments import ExperimentExecutionService
from app.modules.agents.domain.models import (
    GovernedPublishedAgent as PublishedAgent,
)
from app.modules.agents.domain.models import (
    compute_source_fingerprint,
)
from app.modules.datasets.domain.models import DatasetSample, DatasetVersion
from app.modules.experiments.application.ports import ExperimentSampleExecution
from app.modules.experiments.domain.models import ExperimentRecord, ExperimentSpec, ExperimentStatus
from app.modules.shared.domain.enums import AdapterKind
from app.modules.shared.domain.jobs import EnqueuedExecutionJob
from app.modules.shared.domain.models import (
    ApprovalPolicySnapshot,
    EvaluatorConfig,
    ModelConfig,
    PromptConfig,
    ToolsetConfig,
    build_source_execution_reference,
)
from app.modules.shared.domain.models import (
    ExecutionProfile as ExecutorConfig,
)


class StubExperimentRepository:
    def __init__(self, experiment: ExperimentRecord) -> None:
        self.experiment = experiment
        self.saved: list[ExperimentRecord] = []

    def get(self, experiment_id: str | UUID) -> ExperimentRecord | None:
        if self.experiment.experiment_id == UUID(str(experiment_id)):
            return self.experiment
        return None

    def save(self, experiment: ExperimentRecord) -> None:
        self.experiment = experiment
        self.saved.append(experiment)


class StubDatasetRepository:
    def __init__(self, dataset_version: DatasetVersion) -> None:
        self.dataset_version = dataset_version

    def get_version(self, dataset_version_id: str | UUID) -> DatasetVersion | None:
        if self.dataset_version.dataset_version_id == UUID(str(dataset_version_id)):
            return self.dataset_version
        return None


class StubAgentCatalog:
    def __init__(self, agent: PublishedAgent) -> None:
        self.agent = agent

    def get_agent(self, agent_id: str) -> PublishedAgent | None:
        if self.agent.agent_id == agent_id:
            return self.agent
        return None


class StubRunLauncher:
    def __init__(self) -> None:
        self.calls: list[tuple[ExperimentRecord, ExperimentSampleExecution, PublishedAgent]] = []

    def launch(
        self,
        experiment: ExperimentRecord,
        sample: ExperimentSampleExecution,
        agent: PublishedAgent,
    ) -> None:
        self.calls.append((experiment, sample, agent))
        return None


class StubJobQueue:
    def __init__(self) -> None:
        self.enqueued: list[EnqueuedExecutionJob] = []

    def enqueue_run_execution(self, run_spec, *, job_id: str) -> None:
        raise AssertionError("not expected")

    def enqueue_experiment_execution(self, experiment_id) -> None:
        raise AssertionError("not expected")

    def enqueue_experiment_aggregation(self, experiment_id) -> None:
        self.enqueued.append(
            EnqueuedExecutionJob(
                job_id=f"experiment-aggregation:{experiment_id}",
                kind="refresh_experiment_job",
                kwargs={"experiment_id": str(experiment_id)},
            )
        )


def test_experiment_execution_service_launches_sample_descriptors() -> None:
    dataset_version = DatasetVersion(
        dataset_version_id=uuid4(),
        dataset_name="support-dataset",
        rows=[
            DatasetSample(sample_id="sample-1", input="alpha", tags=["shipping"]),
            DatasetSample(sample_id="sample-2", input="beta", tags=["returns"]),
        ],
    )
    experiment = ExperimentRecord(
        experiment_id=uuid4(),
        name="candidate",
        dataset_name=dataset_version.dataset_name,
        dataset_version_id=dataset_version.dataset_version_id,
        published_agent_id="triage-bot",
        status=ExperimentStatus.QUEUED,
        tags=["candidate"],
        sample_count=2,
        spec=ExperimentSpec(
            dataset_version_id=dataset_version.dataset_version_id,
            published_agent_id="triage-bot",
            model_settings=ModelConfig(model="gpt-5.4", temperature=0.0),
            prompt_config=PromptConfig(prompt_version="2026-03", system_prompt="Be strict."),
            toolset_config=ToolsetConfig(tools=["search"]),
            evaluator_config=EvaluatorConfig(metadata={"kind": "exact"}),
            executor_config=ExecutorConfig(backend="local-runner", tracing_backend="phoenix"),
            approval_policy=ApprovalPolicySnapshot(name="default"),
            tags=["candidate"],
        ),
    )
    agent = PublishedAgent.from_snapshot(
        {
            "manifest": AgentManifest(
                agent_id="triage-bot",
                name="Triage Bot",
                description="Checks routing and summarizes issues.",
                framework=AdapterKind.OPENAI_AGENTS.value,
                default_model="gpt-5.4-mini",
                tags=["ops"],
            ).model_dump(mode="json"),
            "entrypoint": "tests.fixtures.agents.triage_bot:build_agent",
        }
    )
    source_fingerprint = compute_source_fingerprint(agent.manifest, agent.entrypoint)
    execution_reference = ExecutionReference.model_validate(
        build_source_execution_reference(
            agent_id=agent.agent_id,
            source_fingerprint=source_fingerprint,
        ).model_dump(mode="json")
    )
    agent.source_fingerprint = source_fingerprint
    agent.execution_reference = execution_reference

    experiment_repository = StubExperimentRepository(experiment)
    run_launcher = StubRunLauncher()
    job_queue = StubJobQueue()
    service = ExperimentExecutionService(
        experiment_repository=experiment_repository,
        dataset_repository=StubDatasetRepository(dataset_version),
        agent_catalog=StubAgentCatalog(agent),
        run_launcher=run_launcher,
        job_queue=job_queue,
    )

    service.execute_experiment(experiment.experiment_id)

    assert experiment_repository.experiment.status == ExperimentStatus.RUNNING
    assert len(run_launcher.calls) == 2

    first_experiment, first_sample, first_agent = run_launcher.calls[0]
    assert first_experiment.experiment_id == experiment.experiment_id
    assert first_agent.agent_id == "triage-bot"
    assert first_sample.dataset_version_id == dataset_version.dataset_version_id
    assert first_sample.dataset_name == "support-dataset"
    assert first_sample.dataset_sample_id == "sample-1"
    assert first_sample.input == "alpha"
    assert first_sample.tags == ["shipping"]

    _second_experiment, second_sample, _ = run_launcher.calls[1]
    assert second_sample.dataset_sample_id == "sample-2"
    assert second_sample.tags == ["returns"]

    assert len(job_queue.enqueued) == 1
    queued_job = job_queue.enqueued[0]
    assert queued_job.kind == "refresh_experiment_job"
    assert queued_job.job_id == f"experiment-aggregation:{experiment.experiment_id}"
    assert queued_job.kwargs == {"experiment_id": str(experiment.experiment_id)}


def test_experiment_execution_service_inherits_published_runtime_profile_when_no_override() -> None:
    dataset_version = DatasetVersion(
        dataset_version_id=uuid4(),
        dataset_name="support-dataset",
        rows=[DatasetSample(sample_id="sample-1", input="alpha", tags=["shipping"])],
    )
    experiment = ExperimentRecord(
        experiment_id=uuid4(),
        name="candidate",
        dataset_name=dataset_version.dataset_name,
        dataset_version_id=dataset_version.dataset_version_id,
        published_agent_id="triage-bot",
        status=ExperimentStatus.QUEUED,
        tags=["candidate"],
        sample_count=1,
        spec=ExperimentSpec(
            dataset_version_id=dataset_version.dataset_version_id,
            published_agent_id="triage-bot",
            model_settings=ModelConfig(model="gpt-5.4", temperature=0.0),
            prompt_config=PromptConfig(prompt_version="2026-03", system_prompt="Be strict."),
            toolset_config=ToolsetConfig(tools=["search"]),
            evaluator_config=EvaluatorConfig(metadata={"kind": "exact"}),
            approval_policy=ApprovalPolicySnapshot(name="default"),
            tags=["candidate"],
        ),
    )
    agent = PublishedAgent.from_snapshot(
        {
            "manifest": AgentManifest(
                agent_id="triage-bot",
                name="Triage Bot",
                description="Checks routing and summarizes issues.",
                framework=AdapterKind.OPENAI_AGENTS.value,
                default_model="gpt-5.4-mini",
                tags=["ops"],
            ).model_dump(mode="json"),
            "entrypoint": "tests.fixtures.agents.triage_bot:build_agent",
        },
        default_runtime_profile=ExecutorConfig(backend="local-runner", tracing_backend="phoenix"),
    )
    source_fingerprint = compute_source_fingerprint(agent.manifest, agent.entrypoint)
    execution_reference = ExecutionReference.model_validate(
        build_source_execution_reference(
            agent_id=agent.agent_id,
            source_fingerprint=source_fingerprint,
        ).model_dump(mode="json")
    )
    agent.source_fingerprint = source_fingerprint
    agent.execution_reference = execution_reference

    experiment_repository = StubExperimentRepository(experiment)
    run_launcher = StubRunLauncher()
    job_queue = StubJobQueue()
    service = ExperimentExecutionService(
        experiment_repository=experiment_repository,
        dataset_repository=StubDatasetRepository(dataset_version),
        agent_catalog=StubAgentCatalog(agent),
        run_launcher=run_launcher,
        job_queue=job_queue,
    )

    service.execute_experiment(experiment.experiment_id)

    _first_experiment, first_sample, _first_agent = run_launcher.calls[0]
    assert first_sample.dataset_sample_id == "sample-1"
    assert first_sample.input == "alpha"


def test_experiment_execution_service_uses_stored_agent_snapshot_when_catalog_changes() -> None:
    dataset_version = DatasetVersion(
        dataset_version_id=uuid4(),
        dataset_name="support-dataset",
        rows=[DatasetSample(sample_id="sample-1", input="alpha", tags=["shipping"])],
    )
    agent = PublishedAgent.from_snapshot(
        {
            "manifest": AgentManifest(
                agent_id="triage-bot",
                name="Triage Bot",
                description="Checks routing and summarizes issues.",
                framework=AdapterKind.OPENAI_AGENTS.value,
                default_model="gpt-5.4-mini",
                tags=["ops"],
            ).model_dump(mode="json"),
            "entrypoint": "tests.fixtures.agents.triage_bot:build_agent",
        },
        default_runtime_profile=ExecutorConfig(backend="local-runner", tracing_backend="phoenix"),
    )
    source_fingerprint = compute_source_fingerprint(agent.manifest, agent.entrypoint)
    execution_reference = ExecutionReference.model_validate(
        build_source_execution_reference(
            agent_id=agent.agent_id,
            source_fingerprint=source_fingerprint,
        ).model_dump(mode="json")
    )
    agent.source_fingerprint = source_fingerprint
    agent.execution_reference = execution_reference

    experiment = ExperimentRecord(
        experiment_id=uuid4(),
        name="candidate",
        dataset_name=dataset_version.dataset_name,
        dataset_version_id=dataset_version.dataset_version_id,
        published_agent_id="triage-bot",
        status=ExperimentStatus.QUEUED,
        tags=["candidate"],
        spec=ExperimentSpec(
            dataset_version_id=dataset_version.dataset_version_id,
            published_agent_id="triage-bot",
            model_settings=ModelConfig(model="gpt-5.4", temperature=0.0),
            prompt_config=PromptConfig(prompt_version="2026-03"),
            toolset_config=ToolsetConfig(),
            evaluator_config=EvaluatorConfig(metadata={"kind": "exact"}),
            approval_policy=ApprovalPolicySnapshot(name="default"),
            tags=["candidate"],
        ),
        published_agent_snapshot=agent.to_snapshot(),
        sample_count=1,
    )

    class MissingAgentCatalog:
        def get_agent(self, agent_id: str) -> PublishedAgent | None:
            del agent_id
            return None

    experiment_repository = StubExperimentRepository(experiment)
    run_launcher = StubRunLauncher()
    job_queue = StubJobQueue()
    service = ExperimentExecutionService(
        experiment_repository=experiment_repository,
        dataset_repository=StubDatasetRepository(dataset_version),
        agent_catalog=MissingAgentCatalog(),
        run_launcher=run_launcher,
        job_queue=job_queue,
    )

    service.execute_experiment(experiment.experiment_id)

    assert len(run_launcher.calls) == 1
    _experiment, _sample, submitted_agent = run_launcher.calls[0]
    assert submitted_agent.agent_id == "triage-bot"
