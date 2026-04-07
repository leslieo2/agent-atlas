from __future__ import annotations

from agent_atlas_contracts.runtime import (
    AgentManifest,
    ExecutionReferenceMetadata as ExecutionReference,
)

from app.modules.agents.application.use_cases import (
    AgentIntakeCommands,
    AgentValidationCommands,
    GovernedAgentIntake,
)
from app.modules.agents.domain.models import (
    ExecutionBinding,
    PublishedAgent,
    compute_source_fingerprint,
)
from app.modules.agents.domain.reference_assets import (
    CLAUDE_CODE_STARTER_ENTRYPOINT,
    claude_code_starter_execution_binding,
    claude_code_starter_manifest,
    claude_code_starter_runtime_profile,
    ensure_claude_code_starter_runtime_ready,
)
from app.modules.runs.domain.models import RunCreateInput, RunRecord
from app.modules.shared.domain.models import build_source_execution_reference


class _Catalog:
    def __init__(self, agent: PublishedAgent) -> None:
        self._agent = agent

    def list_agents(self) -> list[PublishedAgent]:
        return [self._agent]

    def get_agent(self, agent_id: str) -> PublishedAgent | None:
        if self._agent.agent_id == agent_id:
            return self._agent
        return None


class _PublishedAgents:
    def __init__(self) -> None:
        self.saved: list[PublishedAgent] = []
        self.by_id: dict[str, PublishedAgent] = {}

    def list_agents(self) -> list[PublishedAgent]:
        return list(self.by_id.values())

    def get_agent(self, agent_id: str) -> PublishedAgent | None:
        return self.by_id.get(agent_id)

    def save_agent(self, agent: PublishedAgent) -> None:
        self.saved.append(agent)
        self.by_id[agent.agent_id] = agent


class _FrameworkRegistry:
    def __init__(self) -> None:
        self.calls: list[PublishedAgent] = []

    def build_agent(self, *, published_agent: PublishedAgent, context) -> object:
        self.calls.append(published_agent)
        return object()


class _SubmissionService:
    def __init__(self) -> None:
        self.calls: list[tuple[RunCreateInput, PublishedAgent]] = []

    def submit(self, payload: RunCreateInput, agent: PublishedAgent) -> RunRecord:
        self.calls.append((payload, agent))
        return RunRecord(
            project=payload.project,
            dataset=payload.dataset,
            input_summary=payload.input_summary,
            agent_id=agent.agent_id,
            model=agent.default_model,
            agent_type=agent.adapter_kind(),
        )


def _starter_published_agent() -> PublishedAgent:
    manifest = claude_code_starter_manifest()
    source_fingerprint = compute_source_fingerprint(manifest, CLAUDE_CODE_STARTER_ENTRYPOINT)
    execution_reference = ExecutionReference.model_validate(
        build_source_execution_reference(
            agent_id=manifest.agent_id,
            source_fingerprint=source_fingerprint,
        ).model_dump(mode="json")
    )
    return PublishedAgent(
        manifest=manifest,
        entrypoint=CLAUDE_CODE_STARTER_ENTRYPOINT,
        source_fingerprint=source_fingerprint,
        execution_reference=execution_reference,
        execution_binding=claude_code_starter_execution_binding(),
    )


def test_agent_validation_commands_prepares_runtime_from_persisted_execution_binding(
    monkeypatch,
) -> None:
    recorded_bindings = []
    monkeypatch.setattr(
        "app.modules.agents.application.use_cases.ensure_claude_code_starter_runtime_ready",
        lambda binding=None: recorded_bindings.append(binding),
    )
    agent = _starter_published_agent()
    submission = _SubmissionService()
    commands = AgentValidationCommands(_Catalog(agent), submission)

    payload = RunCreateInput(
        agent_id=agent.agent_id,
        project="atlas-validation",
        dataset="controlled-validation",
        input_summary="validate starter",
        prompt="alpha",
    )

    run = commands.create_run(agent.agent_id, payload)

    assert run.agent_id == agent.agent_id
    assert submission.calls == [(payload, agent)]
    assert recorded_bindings == [agent.execution_binding]


def test_governed_agent_intake_can_use_starter_bridge_defaults() -> None:
    intake = GovernedAgentIntake(
        manifest=claude_code_starter_manifest(),
        entrypoint=CLAUDE_CODE_STARTER_ENTRYPOINT,
        default_runtime_profile=claude_code_starter_runtime_profile(),
        execution_binding=claude_code_starter_execution_binding(),
        prepare_runtime=ensure_claude_code_starter_runtime_ready,
    )

    assert intake.manifest.agent_id == "claude-code-starter"
    assert intake.entrypoint == CLAUDE_CODE_STARTER_ENTRYPOINT
    assert intake.default_runtime_profile == claude_code_starter_runtime_profile()
    assert intake.execution_binding == claude_code_starter_execution_binding()
    assert intake.prepare_runtime is ensure_claude_code_starter_runtime_ready


def test_agent_intake_commands_publish_governed_intake_runs_generic_hooks(
    monkeypatch,
) -> None:
    published_agents = _PublishedAgents()
    commands = AgentIntakeCommands(published_agents, _FrameworkRegistry())
    prepared_bindings: list[ExecutionBinding | None] = []
    validated_agents: list[str] = []
    monkeypatch.setattr(
        commands,
        "validate_runnable_intake_candidate",
        lambda agent: validated_agents.append(agent.agent_id),
    )
    intake = GovernedAgentIntake(
        manifest=AgentManifest(
            agent_id="basic",
            name="Basic",
            description="Minimal fixture agent for Atlas execution smoke tests.",
            framework="openai-agents-sdk",
            default_model="gpt-5.4-mini",
            agent_family="openai-agents",
            framework_version="1.0.0",
            tags=["example", "import"],
            capabilities=["submit"],
        ),
        entrypoint="tests.fixtures.agents.basic:build_agent",
        execution_binding=ExecutionBinding(runner_backend="local-process"),
        requires_runnable_validation=True,
        prepare_runtime=lambda binding: prepared_bindings.append(binding),
    )

    published = commands.publish_governed_intake(intake)

    assert published.agent_id == "basic"
    assert prepared_bindings == [published.execution_binding]
    assert validated_agents == ["basic"]
    assert published_agents.saved == [published]
