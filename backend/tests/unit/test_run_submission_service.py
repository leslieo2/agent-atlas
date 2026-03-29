from __future__ import annotations

import pytest
from app.core.errors import AgentFrameworkMismatchError
from app.infrastructure.adapters.artifact_builder import SourceArtifactBuilder
from app.modules.agents.domain.models import AgentManifest, PublishedAgent
from app.modules.runs.application.services import RunSubmissionService
from app.modules.runs.domain.models import RunCreateInput, RunRecord
from app.modules.shared.domain.enums import AdapterKind
from app.modules.shared.domain.tasks import QueuedTask, TaskType


class StubRunRepository:
    def __init__(self) -> None:
        self.saved: list[RunRecord] = []

    def get(self, run_id: object) -> RunRecord | None:
        for run in self.saved:
            if run.run_id == run_id:
                return run
        return None

    def list(self) -> list[RunRecord]:
        return list(self.saved)

    def save(self, run: RunRecord) -> None:
        self.saved.append(run)


class StubTaskQueue:
    def __init__(self) -> None:
        self.enqueued: list[QueuedTask] = []

    def enqueue(self, task: QueuedTask) -> None:
        self.enqueued.append(task)


def test_run_submission_service_uses_published_agent_framework_and_enqueues_execution() -> None:
    repository = StubRunRepository()
    task_queue = StubTaskQueue()
    service = RunSubmissionService(run_repository=repository, task_queue=task_queue)
    payload = RunCreateInput(
        project="migration-check",
        dataset="framework-ds",
        agent_id="triage-bot",
        input_summary="framework coverage",
        prompt="Inspect the latest run.",
        tags=["regression", "langchain"],
        project_metadata={"team": "platform"},
    )
    agent = PublishedAgent(
        manifest=AgentManifest(
            agent_id="triage-bot",
            name="Triage Bot",
            description="Checks routing and summarizes issues.",
            framework=AdapterKind.LANGCHAIN.value,
            default_model="gpt-5.4-mini",
            tags=["ops"],
        ),
        entrypoint="app.agent_plugins.triage_bot:build_agent",
    )
    build_result = SourceArtifactBuilder().build(agent)
    agent.runtime_artifact = build_result.runtime_artifact
    agent.provenance = build_result.provenance

    run = service.submit(payload, agent)

    assert run.agent_type == AdapterKind.LANGCHAIN
    assert run.model == "gpt-5.4-mini"
    assert run.provenance is not None
    assert run.provenance.framework == "langchain"
    assert run.provenance.published_agent_snapshot is not None
    assert run.provenance.published_agent_snapshot["manifest"]["framework"] == "langchain"
    assert run.provenance.published_agent_snapshot["runtime_artifact"]["build_status"] == "ready"
    assert run.provenance.artifact_ref == build_result.runtime_artifact.artifact_ref
    assert repository.saved == [run]
    assert len(task_queue.enqueued) == 1
    task = task_queue.enqueued[0]
    assert task.task_type == TaskType.RUN_EXECUTION
    assert task.target_id == run.run_id
    assert task.payload["agent_type"] == AdapterKind.LANGCHAIN.value
    assert task.payload["entrypoint"] == "app.agent_plugins.triage_bot:build_agent"
    assert task.payload["provenance"]["framework"] == "langchain"


def test_run_submission_service_rejects_mismatched_snapshot_framework() -> None:
    repository = StubRunRepository()
    task_queue = StubTaskQueue()
    service = RunSubmissionService(run_repository=repository, task_queue=task_queue)
    payload = RunCreateInput(
        project="migration-check",
        dataset="framework-ds",
        agent_id="triage-bot",
        input_summary="framework coverage",
        prompt="Inspect the latest run.",
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
        entrypoint="app.agent_plugins.triage_bot:build_agent",
    )
    build_result = SourceArtifactBuilder().build(agent)
    agent.runtime_artifact = build_result.runtime_artifact
    agent.provenance = build_result.provenance
    assert agent.provenance is not None
    assert agent.provenance.published_agent_snapshot is not None
    agent.provenance.published_agent_snapshot["manifest"]["framework"] = AdapterKind.LANGCHAIN.value

    with pytest.raises(AgentFrameworkMismatchError):
        service.submit(payload, agent)

    assert repository.saved == []
    assert task_queue.enqueued == []


def test_run_submission_service_backfills_legacy_artifact_handoff() -> None:
    repository = StubRunRepository()
    task_queue = StubTaskQueue()
    service = RunSubmissionService(run_repository=repository, task_queue=task_queue)
    payload = RunCreateInput(
        project="legacy-handoff",
        agent_id="triage-bot",
        input_summary="legacy handoff",
        prompt="Inspect the latest run.",
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
        entrypoint="app.agent_plugins.triage_bot:build_agent",
        source_fingerprint="legacy-fingerprint",
    )

    run = service.submit(payload, agent)

    assert run.provenance is not None
    assert run.provenance.artifact_ref == "source://triage-bot@legacy-fingerprint"
    assert run.provenance.published_agent_snapshot is not None
    assert run.provenance.published_agent_snapshot["runtime_artifact"]["source_fingerprint"] == (
        "legacy-fingerprint"
    )
