from __future__ import annotations

from uuid import UUID, uuid4

from agent_atlas_contracts.runtime import (
    AgentManifest,
)
from agent_atlas_contracts.runtime import (
    ExecutionReferenceMetadata as ExecutionReference,
)
from app.modules.agents.domain.models import PublishedAgent, compute_source_fingerprint
from app.modules.datasets.domain.models import DatasetSample, DatasetVersion
from app.modules.experiments.application.execution import ExperimentOrchestrator
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


class StubRunSubmission:
    def __init__(self) -> None:
        self.calls: list[tuple[object, PublishedAgent]] = []

    def submit(self, payload, agent: PublishedAgent):
        self.calls.append((payload, agent))
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


def test_experiment_orchestrator_submits_runs_via_run_submission_service() -> None:
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
    agent = PublishedAgent(
        manifest=AgentManifest(
            agent_id="triage-bot",
            name="Triage Bot",
            description="Checks routing and summarizes issues.",
            framework=AdapterKind.OPENAI_AGENTS.value,
            default_model="gpt-5.4-mini",
            tags=["ops"],
        ),
        entrypoint="tests.fixtures.agents.triage_bot:build_agent",
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
    run_submission = StubRunSubmission()
    job_queue = StubJobQueue()
    orchestrator = ExperimentOrchestrator(
        experiment_repository=experiment_repository,
        dataset_repository=StubDatasetRepository(dataset_version),
        agent_catalog=StubAgentCatalog(agent),
        run_submission=run_submission,
        job_queue=job_queue,
    )

    orchestrator.execute_experiment(experiment.experiment_id)

    assert experiment_repository.experiment.status == ExperimentStatus.RUNNING
    assert len(run_submission.calls) == 2

    first_payload, first_agent = run_submission.calls[0]
    assert first_agent.agent_id == "triage-bot"
    assert first_payload.experiment_id == experiment.experiment_id
    assert first_payload.dataset_version_id == dataset_version.dataset_version_id
    assert first_payload.dataset == "support-dataset"
    assert first_payload.dataset_sample_id == "sample-1"
    assert first_payload.model_settings is not None
    assert first_payload.model_settings.model == "gpt-5.4"
    assert first_payload.executor_config.backend == "local-runner"
    assert first_payload.executor_config.tracing_backend == "phoenix"
    assert first_payload.tags == ["candidate", "shipping"]
    assert first_payload.project_metadata == {
        "prompt_version": "2026-03",
        "system_prompt": "Be strict.",
    }

    second_payload, _ = run_submission.calls[1]
    assert second_payload.dataset_sample_id == "sample-2"
    assert second_payload.tags == ["candidate", "returns"]

    assert len(job_queue.enqueued) == 1
    queued_job = job_queue.enqueued[0]
    assert queued_job.kind == "refresh_experiment_job"
    assert queued_job.job_id == f"experiment-aggregation:{experiment.experiment_id}"
    assert queued_job.kwargs == {"experiment_id": str(experiment.experiment_id)}


def test_experiment_orchestrator_inherits_published_runtime_profile_when_no_override() -> None:
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
    agent = PublishedAgent(
        manifest=AgentManifest(
            agent_id="triage-bot",
            name="Triage Bot",
            description="Checks routing and summarizes issues.",
            framework=AdapterKind.OPENAI_AGENTS.value,
            default_model="gpt-5.4-mini",
            tags=["ops"],
        ),
        entrypoint="tests.fixtures.agents.triage_bot:build_agent",
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
    run_submission = StubRunSubmission()
    job_queue = StubJobQueue()
    orchestrator = ExperimentOrchestrator(
        experiment_repository=experiment_repository,
        dataset_repository=StubDatasetRepository(dataset_version),
        agent_catalog=StubAgentCatalog(agent),
        run_submission=run_submission,
        job_queue=job_queue,
    )

    orchestrator.execute_experiment(experiment.experiment_id)

    first_payload, _first_agent = run_submission.calls[0]
    assert "executor_config" not in first_payload.model_fields_set


def test_experiment_orchestrator_uses_stored_agent_snapshot_when_catalog_changes() -> None:
    dataset_version = DatasetVersion(
        dataset_version_id=uuid4(),
        dataset_name="support-dataset",
        rows=[DatasetSample(sample_id="sample-1", input="alpha", tags=["shipping"])],
    )
    agent = PublishedAgent(
        manifest=AgentManifest(
            agent_id="triage-bot",
            name="Triage Bot",
            description="Checks routing and summarizes issues.",
            framework=AdapterKind.OPENAI_AGENTS.value,
            default_model="gpt-5.4-mini",
            tags=["ops"],
        ),
        entrypoint="tests.fixtures.agents.triage_bot:build_agent",
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
    run_submission = StubRunSubmission()
    job_queue = StubJobQueue()
    orchestrator = ExperimentOrchestrator(
        experiment_repository=experiment_repository,
        dataset_repository=StubDatasetRepository(dataset_version),
        agent_catalog=MissingAgentCatalog(),
        run_submission=run_submission,
        job_queue=job_queue,
    )

    orchestrator.execute_experiment(experiment.experiment_id)

    assert len(run_submission.calls) == 1
    _payload, submitted_agent = run_submission.calls[0]
    assert submitted_agent.agent_id == "triage-bot"
