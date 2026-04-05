from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from uuid import UUID

from app.core.errors import (
    AgentImportConflictError,
    AgentLoadFailedError,
    AgentValidationFailedError,
    PublishedAgentNotFoundError,
)
from app.modules.agents.application.ports import (
    AgentValidationRecordPort,
    FrameworkRegistryPort,
    PublishedAgentCatalogPort,
    PublishedAgentRepositoryPort,
)
from app.modules.agents.domain.models import (
    AgentBuildContext,
    AgentManifest,
    AgentValidationEvidenceSummary,
    AgentValidationOutcomeStatus,
    AgentValidationOutcomeSummary,
    AgentValidationRecord,
    AgentValidationRunReference,
    ExecutionBinding,
    ExecutionReference,
    PublishedAgent,
    compute_source_fingerprint,
)
from app.modules.agents.domain.reference_assets import (
    CLAUDE_CODE_STARTER_AGENT_ID,
    ensure_claude_code_starter_runtime_ready,
    get_governed_reference_asset,
)
from app.modules.runs.application.services import RunSubmissionService
from app.modules.runs.domain.models import RunCreateInput, RunRecord
from app.modules.shared.domain.constants import EXTERNAL_RUNNER_EXECUTION_BACKEND
from app.modules.shared.domain.models import ExecutorConfig, build_source_execution_reference


class PublishedAgentCatalogQueries:
    def __init__(
        self,
        published_agents: PublishedAgentCatalogPort,
        validation_records: AgentValidationRecordPort,
    ) -> None:
        self.published_agents = published_agents
        self.validation_records = validation_records

    def list_agents(self) -> list[PublishedAgent]:
        latest_validation_by_agent = _latest_validation_runs(self.validation_records.list_records())
        valid_agents = [
            _attach_validation_summary(agent, latest_validation_by_agent.get(agent.agent_id))
            for agent in self.published_agents.list_agents()
            if _is_valid_published_agent(agent)
        ]
        return sorted(valid_agents, key=lambda agent: agent.agent_id)


def _latest_validation_runs(
    records: Iterable[AgentValidationRecord],
) -> dict[str, AgentValidationRecord]:
    latest_by_agent: dict[str, AgentValidationRecord] = {}
    ordered = sorted(records, key=lambda record: record.created_at, reverse=True)
    for record in ordered:
        if not record.agent_id:
            continue
        latest_by_agent.setdefault(record.agent_id, record)
    return latest_by_agent


def _validation_outcome_status(record: AgentValidationRecord) -> AgentValidationOutcomeStatus:
    if record.status == "succeeded":
        return AgentValidationOutcomeStatus.PASSED
    if record.status in {"failed", "cancelled", "lost"}:
        return AgentValidationOutcomeStatus.FAILED
    return AgentValidationOutcomeStatus.RUNNING


def _attach_validation_summary(
    agent: PublishedAgent,
    record: AgentValidationRecord | None,
) -> PublishedAgent:
    if record is None:
        return agent

    return agent.model_copy(
        update={
            "latest_validation": AgentValidationRunReference(
                run_id=record.run_id,
                status=record.status,
                created_at=record.created_at,
                started_at=record.started_at,
                completed_at=record.completed_at,
            ),
            "validation_evidence": AgentValidationEvidenceSummary(
                artifact_ref=record.artifact_ref,
                image_ref=record.image_ref,
                trace_url=record.trace_url,
                terminal_summary=record.terminal_summary,
            ),
            "validation_outcome": AgentValidationOutcomeSummary(
                status=_validation_outcome_status(record),
                reason=record.terminal_summary,
            ),
        },
        deep=True,
    )


def _is_valid_published_agent(agent: PublishedAgent) -> bool:
    try:
        agent.source_fingerprint_or_raise()
        agent.execution_reference_or_raise()
    except ValueError:
        return False
    return True


def _governed_execution_reference(*, agent_id: str, source_fingerprint: str) -> ExecutionReference:
    return ExecutionReference.model_validate(
        build_source_execution_reference(
            agent_id=agent_id,
            source_fingerprint=source_fingerprint,
        ).model_dump(mode="json")
    )


def _import_execution_binding() -> ExecutionBinding:
    return ExecutionBinding(runner_backend="local-process")


def _intake_validation_context() -> AgentBuildContext:
    return AgentBuildContext(
        run_id=UUID("00000000-0000-0000-0000-000000000000"),
        project="agent-import-validation",
        dataset=None,
        prompt="validation",
        tags=["agent-import"],
        project_metadata={"source": "governed-intake"},
    )


@dataclass(frozen=True)
class _GovernedIntakePlan:
    manifest: AgentManifest
    entrypoint: str
    default_runtime_profile: ExecutorConfig | None = None
    execution_binding: ExecutionBinding | None = None
    validate_candidate: Callable[[PublishedAgent], None] | None = None
    prepare_runtime: Callable[[ExecutionBinding | None], None] | None = None


def _governed_asset_from_intake(plan: _GovernedIntakePlan) -> PublishedAgent:
    manifest = plan.manifest.model_copy(deep=True)
    source_fingerprint = compute_source_fingerprint(manifest, plan.entrypoint)
    return PublishedAgent(
        manifest=manifest,
        entrypoint=plan.entrypoint,
        source_fingerprint=source_fingerprint,
        execution_reference=_governed_execution_reference(
            agent_id=manifest.agent_id,
            source_fingerprint=source_fingerprint,
        ),
        default_runtime_profile=(
            plan.default_runtime_profile.model_copy(deep=True)
            if plan.default_runtime_profile is not None
            else ExecutorConfig(backend=EXTERNAL_RUNNER_EXECUTION_BACKEND)
        ),
        execution_binding=(
            plan.execution_binding.model_copy(deep=True)
            if plan.execution_binding is not None
            else None
        ),
    )


def _import_intake_plan(
    manifest: AgentManifest,
    *,
    entrypoint: str,
) -> _GovernedIntakePlan:
    return _GovernedIntakePlan(
        manifest=manifest,
        entrypoint=entrypoint,
        execution_binding=_import_execution_binding(),
    )


def _reference_asset_intake_plan(asset_id: str) -> _GovernedIntakePlan:
    asset = get_governed_reference_asset(asset_id)
    return _GovernedIntakePlan(
        manifest=asset.manifest,
        entrypoint=asset.entrypoint,
        default_runtime_profile=asset.default_runtime_profile,
        execution_binding=asset.execution_binding,
        prepare_runtime=asset.prepare_runtime,
    )


class AgentIntakeCommands:
    def __init__(
        self,
        published_agents: PublishedAgentRepositoryPort,
        framework_registry: FrameworkRegistryPort,
    ) -> None:
        self.published_agents = published_agents
        self.framework_registry = framework_registry

    def create_claude_code_starter(self) -> PublishedAgent:
        return self.publish_reference_asset(CLAUDE_CODE_STARTER_AGENT_ID)

    def publish_reference_asset(self, asset_id: str) -> PublishedAgent:
        reference_asset = get_governed_reference_asset(asset_id)
        existing = self.published_agents.get_agent(reference_asset.asset_id)
        if existing is not None and _is_valid_published_agent(existing):
            return existing

        return self._ingest_governed_asset(_reference_asset_intake_plan(reference_asset.asset_id))

    def import_agent_source(self, *, manifest: AgentManifest, entrypoint: str) -> PublishedAgent:
        return self._ingest_governed_asset(
            _import_intake_plan(manifest, entrypoint=entrypoint),
            validate_candidate=self._validate_runnable_import,
        )

    def _ingest_governed_asset(
        self,
        plan: _GovernedIntakePlan,
        *,
        validate_candidate: Callable[[PublishedAgent], None] | None = None,
    ) -> PublishedAgent:
        candidate = _governed_asset_from_intake(plan)
        if plan.prepare_runtime is not None:
            plan.prepare_runtime(candidate.execution_binding)
        if validate_candidate is not None:
            validate_candidate(candidate)
        elif plan.validate_candidate is not None:
            plan.validate_candidate(candidate)
        self._save_governed_asset(candidate)
        return candidate

    def _save_governed_asset(self, candidate: PublishedAgent) -> None:
        existing = self.published_agents.get_agent(candidate.agent_id)
        if existing is not None and _is_valid_published_agent(existing):
            if (
                existing.source_fingerprint_or_raise() == candidate.source_fingerprint_or_raise()
                and existing.entrypoint == candidate.entrypoint
            ):
                return
            raise AgentImportConflictError(candidate.agent_id)

        self.published_agents.save_agent(candidate)

    def _validate_runnable_import(self, candidate: PublishedAgent) -> None:
        try:
            self.framework_registry.build_agent(
                published_agent=candidate,
                context=_intake_validation_context(),
            )
        except AgentLoadFailedError as exc:
            raise AgentValidationFailedError(candidate.agent_id, str(exc)) from exc
        except Exception as exc:
            raise AgentValidationFailedError(
                candidate.agent_id,
                (
                    f"entrypoint '{candidate.entrypoint}' could not be loaded "
                    f"as a runnable asset: {exc}"
                ),
            ) from exc


class AgentValidationCommands:
    def __init__(
        self,
        published_agents: PublishedAgentCatalogPort,
        submission_service: RunSubmissionService,
    ) -> None:
        self.published_agents = published_agents
        self.submission_service = submission_service

    def create_run(self, agent_id: str, payload: RunCreateInput) -> RunRecord:
        agent = self._resolve_agent(agent_id)
        ensure_claude_code_starter_runtime_ready(agent.execution_binding)
        return self.submission_service.submit(payload, agent)

    def _resolve_agent(self, agent_id: str) -> PublishedAgent:
        existing = self.published_agents.get_agent(agent_id)
        if existing is None or not _is_valid_published_agent(existing):
            raise PublishedAgentNotFoundError(agent_id)
        return existing
