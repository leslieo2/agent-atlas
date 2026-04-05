from __future__ import annotations

from app.modules.agents.application.use_cases import AgentValidationCommands
from app.modules.agents.domain.models import (
    ExecutionReference,
    PublishedAgent,
    compute_source_fingerprint,
)
from app.modules.agents.domain.starter_assets import (
    CLAUDE_CODE_STARTER_ENTRYPOINT,
    claude_code_starter_execution_binding,
    claude_code_starter_manifest,
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
