from __future__ import annotations

import pytest
from app.core.errors import UnsupportedOperationError
from app.execution.contracts import ExecutionRunSpec, RunHandle
from app.modules.agents.domain.models import (
    AgentManifest,
    ExecutionReference,
    PublishedAgent,
    compute_source_fingerprint,
)
from app.modules.runs.adapters.inbound.http.schemas import RunCreateRequest
from app.modules.runs.application.services import RunSubmissionService
from app.modules.runs.domain.models import RunCreateInput, RunRecord
from app.modules.shared.domain.enums import AdapterKind
from app.modules.shared.domain.models import (
    ApprovalPolicySnapshot,
    EvaluatorConfig,
    ExecutorConfig,
    ModelConfig,
    PromptConfig,
    ToolPolicyRule,
    ToolsetConfig,
    build_source_execution_reference,
)
from pydantic import ValidationError


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
        for index, existing in enumerate(self.saved):
            if existing.run_id == run.run_id:
                self.saved[index] = run
                return
        self.saved.append(run)


class StubExecutionControl:
    def __init__(self) -> None:
        self.submitted: list[ExecutionRunSpec] = []

    def submit_run(self, run_spec: ExecutionRunSpec) -> RunHandle:
        self.submitted.append(run_spec)
        return RunHandle(
            run_id=run_spec.run_id,
            backend=run_spec.executor_config.backend,
            executor_ref=f"local-{run_spec.run_id}",
        )


def _seal_agent(agent: PublishedAgent) -> tuple[PublishedAgent, str]:
    source_fingerprint = compute_source_fingerprint(agent.manifest, agent.entrypoint)
    execution_reference = ExecutionReference.model_validate(
        build_source_execution_reference(
            agent_id=agent.agent_id,
            source_fingerprint=source_fingerprint,
        ).model_dump(mode="json")
    )
    agent.source_fingerprint = source_fingerprint
    agent.execution_reference = execution_reference
    return agent, execution_reference.artifact_ref or ""


def test_run_create_input_defaults_to_executor_config_external_runner() -> None:
    payload = RunCreateInput(
        project="migration-check",
        dataset="framework-ds",
        agent_id="triage-bot",
        input_summary="framework coverage",
        prompt="Inspect the latest run.",
    )

    assert payload.executor_config.backend == "external-runner"


def test_run_submission_service_uses_published_agent_framework_and_enqueues_execution() -> None:
    repository = StubRunRepository()
    execution_control = StubExecutionControl()
    service = RunSubmissionService(
        run_repository=repository,
        execution_control=execution_control,
    )
    payload = RunCreateInput(
        project="migration-check",
        dataset="framework-ds",
        agent_id="triage-bot",
        input_summary="framework coverage",
        prompt="Inspect the latest run.",
        tags=["regression", "langchain"],
        project_metadata={"team": "platform"},
        executor_config=ExecutorConfig(backend="local-runner"),
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
    agent, artifact_ref = _seal_agent(agent)

    run = service.submit(payload, agent)

    assert run.agent_type == AdapterKind.LANGCHAIN
    assert run.model == "gpt-5.4-mini"
    assert run.provenance is not None
    assert run.provenance.framework == "langchain"
    assert run.provenance.published_agent_snapshot is not None
    assert run.provenance.published_agent_snapshot["manifest"]["framework"] == "langchain"
    assert run.provenance.published_agent_snapshot["source_fingerprint"] == agent.source_fingerprint
    assert (
        run.provenance.published_agent_snapshot["execution_reference"]["artifact_ref"]
        == artifact_ref
    )
    assert run.provenance.artifact_ref == artifact_ref
    assert repository.saved == [run]
    assert len(execution_control.submitted) == 1
    task = execution_control.submitted[0]
    assert run.executor_backend == "local-runner"
    assert run.executor_submission_id == f"local-{run.run_id}"
    assert task.agent_type == AdapterKind.LANGCHAIN
    assert task.entrypoint == "app.agent_plugins.triage_bot:build_agent"
    assert task.provenance is not None
    assert task.provenance.framework == "langchain"


def test_run_submission_service_deep_merges_nested_runtime_profile_overrides() -> None:
    repository = StubRunRepository()
    execution_control = StubExecutionControl()
    service = RunSubmissionService(
        run_repository=repository,
        execution_control=execution_control,
    )
    payload = RunCreateInput(
        project="migration-check",
        dataset="framework-ds",
        agent_id="triage-bot",
        input_summary="framework coverage",
        prompt="Inspect the latest run.",
        executor_config=ExecutorConfig(
            backend="local-runner",
            resources={"cpu": "2000m"},
            metadata={"team": "evals"},
        ),
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
        default_runtime_profile=ExecutorConfig(
            backend="k8s-job",
            runner_image="ghcr.io/example/atlas-runner:published",
            resources={"cpu": "1000m", "memory": "2Gi"},
            metadata={"team": "platform", "region": "us-east-1"},
        ),
    )
    sealed_agent, _artifact_ref = _seal_agent(agent)

    run = service.submit(payload, sealed_agent)

    assert run.provenance is not None
    executor = execution_control.submitted[0].executor_config
    assert executor.backend == "local-runner"
    assert executor.runner_image == "ghcr.io/example/atlas-runner:published"
    assert executor.resources.cpu == "2000m"
    assert executor.resources.memory == "2Gi"
    assert executor.metadata == {"team": "evals", "region": "us-east-1"}


def test_run_submission_service_uses_injected_default_trace_backend_when_executor_config_missing():
    repository = StubRunRepository()
    execution_control = StubExecutionControl()
    service = RunSubmissionService(
        run_repository=repository,
        execution_control=execution_control,
        default_trace_backend="phoenix",
    )
    payload = RunCreateInput(
        project="migration-check",
        dataset="framework-ds",
        agent_id="triage-bot",
        input_summary="framework coverage",
        prompt="Inspect the latest run.",
        executor_config=ExecutorConfig(backend="local-runner"),
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
    agent, _artifact_ref = _seal_agent(agent)

    run = service.submit(payload, agent)

    assert run.provenance is not None
    assert run.provenance.trace_backend == "phoenix"
    assert run.provenance.executor is not None
    assert run.provenance.executor.tracing_backend == "phoenix"
    assert execution_control.submitted[0].executor_config.tracing_backend == "phoenix"


def test_run_submission_service_uses_injected_default_trace_backend_when_executor_config_omits_it():
    repository = StubRunRepository()
    execution_control = StubExecutionControl()
    service = RunSubmissionService(
        run_repository=repository,
        execution_control=execution_control,
        default_trace_backend="phoenix",
    )
    payload = RunCreateInput(
        project="migration-check",
        dataset="framework-ds",
        agent_id="triage-bot",
        input_summary="framework coverage",
        prompt="Inspect the latest run.",
        executor_config=ExecutorConfig(
            backend="k8s-job",
            runner_image="ghcr.io/example/atlas-runner:latest",
        ),
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
    agent, _artifact_ref = _seal_agent(agent)

    run = service.submit(payload, agent)

    assert run.provenance is not None
    assert run.provenance.trace_backend == "phoenix"
    assert run.provenance.executor is not None
    assert run.provenance.executor.tracing_backend == "phoenix"
    assert execution_control.submitted[0].executor_config.tracing_backend == "phoenix"


def test_run_submission_service_preserves_agent_default_runtime_profile_trace_backend() -> None:
    repository = StubRunRepository()
    execution_control = StubExecutionControl()
    service = RunSubmissionService(
        run_repository=repository,
        execution_control=execution_control,
        default_trace_backend="phoenix",
    )
    payload = RunCreateInput(
        project="migration-check",
        dataset="framework-ds",
        agent_id="triage-bot",
        input_summary="framework coverage",
        prompt="Inspect the latest run.",
        executor_config=ExecutorConfig(
            backend="k8s-job",
            runner_image="ghcr.io/example/atlas-runner:latest",
        ),
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
        default_runtime_profile=ExecutorConfig(
            backend="k8s-job",
            runner_image="ghcr.io/example/atlas-runner:published",
            tracing_backend="state",
        ),
    )
    agent, _artifact_ref = _seal_agent(agent)

    run = service.submit(payload, agent)

    assert run.provenance is not None
    assert run.provenance.trace_backend == "state"
    assert run.provenance.executor is not None
    assert run.provenance.executor.tracing_backend == "state"
    assert execution_control.submitted[0].executor_config.tracing_backend == "state"


def test_run_submission_service_preserves_requested_model_and_execution_metadata() -> None:
    repository = StubRunRepository()
    execution_control = StubExecutionControl()
    service = RunSubmissionService(
        run_repository=repository,
        execution_control=execution_control,
        default_trace_backend="state",
    )
    payload = RunCreateInput(
        project="experiment-batch",
        dataset="framework-ds",
        dataset_version_id="00000000-0000-0000-0000-000000000123",
        dataset_sample_id="sample-1",
        agent_id="triage-bot",
        input_summary="framework coverage",
        prompt="Inspect the latest run.",
        project_metadata={"team": "platform", "prompt_version": "2026-03"},
        executor_config=ExecutorConfig(
            backend="k8s-job",
            runner_image="ghcr.io/example/atlas-runner:latest",
            tracing_backend="phoenix",
        ),
        model_settings=ModelConfig(model="gpt-5.4"),
        prompt_config=PromptConfig(prompt_version="2026-03", system_prompt="Be strict."),
        toolset_config=ToolsetConfig(tools=["search"]),
        evaluator_config=EvaluatorConfig(metadata={"kind": "exact"}),
        approval_policy=ApprovalPolicySnapshot(
            name="default",
            tool_policies=[ToolPolicyRule(tool_name="search", effect="allow")],
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
        entrypoint="app.agent_plugins.triage_bot:build_agent",
    )
    agent, _artifact_ref = _seal_agent(agent)

    run = service.submit(payload, agent)

    assert run.model == "gpt-5.4"
    assert run.provenance is not None
    assert run.provenance.trace_backend == "phoenix"
    assert run.provenance.executor_backend == "k8s-job"
    assert run.provenance.dataset_sample_id == "sample-1"
    assert run.provenance.toolset is not None
    assert run.provenance.toolset.tools == ["search"]
    assert run.provenance.evaluator is not None
    assert run.provenance.evaluator.metadata == {"kind": "exact"}
    assert run.provenance.approval_policy is not None
    assert run.provenance.approval_policy.name == "default"
    assert run.provenance.executor is not None
    assert run.provenance.executor.tracing_backend == "phoenix"

    submitted = execution_control.submitted[0]
    assert submitted.model == "gpt-5.4"
    assert submitted.provenance is not None
    assert submitted.provenance.trace_backend == "phoenix"


def test_run_submission_service_ignores_stale_legacy_publication_provenance() -> None:
    repository = StubRunRepository()
    execution_control = StubExecutionControl()
    service = RunSubmissionService(
        run_repository=repository,
        execution_control=execution_control,
    )
    payload = RunCreateInput(
        project="migration-check",
        dataset="framework-ds",
        agent_id="triage-bot",
        input_summary="framework coverage",
        prompt="Inspect the latest run.",
        executor_config=ExecutorConfig(backend="local-runner"),
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
    agent, artifact_ref = _seal_agent(agent)
    run = service.submit(payload, agent)

    assert run.provenance is not None
    assert run.provenance.artifact_ref == artifact_ref
    assert run.provenance.published_agent_snapshot is not None
    assert (
        run.provenance.published_agent_snapshot["manifest"]["framework"]
        == AdapterKind.OPENAI_AGENTS.value
    )
    assert len(execution_control.submitted) == 1


def test_run_submission_service_rejects_k8s_job_without_runner_image():
    repository = StubRunRepository()
    execution_control = StubExecutionControl()
    service = RunSubmissionService(
        run_repository=repository,
        execution_control=execution_control,
    )
    payload = RunCreateInput(
        project="migration-check",
        dataset="framework-ds",
        agent_id="triage-bot",
        input_summary="framework coverage",
        prompt="Inspect the latest run.",
        executor_config=ExecutorConfig(backend="k8s-job"),
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
    agent, _artifact_ref = _seal_agent(agent)

    with pytest.raises(UnsupportedOperationError, match="runner_image"):
        service.submit(payload, agent)

    assert repository.saved == []
    assert execution_control.submitted == []


def test_run_submission_service_rejects_k8s_job_with_only_published_image() -> None:
    repository = StubRunRepository()
    execution_control = StubExecutionControl()
    service = RunSubmissionService(
        run_repository=repository,
        execution_control=execution_control,
    )
    payload = RunCreateInput(
        project="migration-check",
        dataset="framework-ds",
        agent_id="triage-bot",
        input_summary="framework coverage",
        prompt="Inspect the latest run.",
        executor_config=ExecutorConfig(backend="k8s-job"),
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
    agent, artifact_ref = _seal_agent(agent)
    agent.execution_reference = agent.execution_reference.model_copy(
        update={
            "artifact_ref": artifact_ref,
            "image_ref": "ghcr.io/example/published-agent:123",
        }
    )

    with pytest.raises(UnsupportedOperationError, match="runner_image"):
        service.submit(payload, agent)

    assert repository.saved == []
    assert execution_control.submitted == []


def test_run_create_input_rejects_legacy_executor_backend_field() -> None:
    with pytest.raises(ValidationError):
        RunCreateInput.model_validate(
            {
                "project": "migration-check",
                "dataset": "framework-ds",
                "agent_id": "triage-bot",
                "input_summary": "framework coverage",
                "prompt": "Inspect the latest run.",
                "executor_backend": "local-runner",
            }
        )


def test_run_create_request_rejects_legacy_executor_backend_field() -> None:
    with pytest.raises(ValidationError):
        RunCreateRequest.model_validate(
            {
                "project": "migration-check",
                "dataset": "framework-ds",
                "agent_id": "triage-bot",
                "input_summary": "framework coverage",
                "prompt": "Inspect the latest run.",
                "executor_backend": "local-runner",
            }
        )
