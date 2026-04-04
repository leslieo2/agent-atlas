from __future__ import annotations

from collections.abc import Iterable
from typing import cast

from app.core.errors import (
    AgentValidationFailedError,
    PublishedAgentNotFoundError,
    UnsupportedOperationError,
)
from app.modules.agents.application.ports import (
    AgentSourceDiscoveryPort,
    AgentValidationRecordPort,
    LiveAgentMarkerRepositoryPort,
    PublishedAgentCatalogPort,
    PublishedAgentRepositoryPort,
)
from app.modules.agents.domain.models import (
    AgentValidationEvidenceSummary,
    AgentValidationOutcomeStatus,
    AgentValidationOutcomeSummary,
    AgentValidationRecord,
    AgentValidationRunReference,
    AgentValidationStatus,
    DiscoveredAgent,
    ExecutionReference,
    PublishedAgent,
    compute_source_fingerprint,
)
from app.modules.agents.domain.starter_assets import (
    CLAUDE_CODE_STARTER_AGENT_ID,
    CLAUDE_CODE_STARTER_ENTRYPOINT,
    claude_code_starter_manifest,
    claude_code_starter_runtime_profile,
    ensure_claude_code_starter_runtime_ready,
)
from app.modules.runs.application.services import RunSubmissionService
from app.modules.runs.domain.models import RunCreateInput, RunRecord
from app.modules.shared.domain.models import build_source_execution_reference


class AgentDiscoveryQueries:
    def __init__(
        self,
        discovery: AgentSourceDiscoveryPort | None,
        published_agents: PublishedAgentRepositoryPort,
        validation_records: AgentValidationRecordPort,
    ) -> None:
        self.discovery = discovery
        self.published_agents = published_agents
        self.validation_records = validation_records

    def list_agents(self) -> list[DiscoveredAgent]:
        if self.discovery is None:
            return []
        published_by_id = {agent.agent_id: agent for agent in self.published_agents.list_agents()}
        latest_validation_by_agent = _latest_validation_runs(self.validation_records.list_records())
        discovered_agents = self.discovery.list_agents()
        enriched_agents: list[DiscoveredAgent] = []
        for agent in discovered_agents:
            published_agent = published_by_id.get(agent.agent_id)
            if published_agent is None or not _is_valid_published_agent(published_agent):
                enriched_agents.append(
                    cast(
                        DiscoveredAgent,
                        _attach_validation_summary(
                            agent.with_publication(None),
                            latest_validation_by_agent.get(agent.agent_id),
                        ),
                    )
                )
                continue
            enriched_agents.append(
                cast(
                    DiscoveredAgent,
                    _attach_validation_summary(
                        agent.with_publication(published_agent),
                        latest_validation_by_agent.get(agent.agent_id),
                    ),
                )
            )
        return enriched_agents


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
            cast(
                PublishedAgent,
                _attach_validation_summary(agent, latest_validation_by_agent.get(agent.agent_id)),
            )
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
    agent: PublishedAgent | DiscoveredAgent,
    record: AgentValidationRecord | None,
) -> PublishedAgent | DiscoveredAgent:
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


class AgentPublicationCommands:
    def __init__(
        self,
        discovery: AgentSourceDiscoveryPort | None,
        published_agents: PublishedAgentRepositoryPort,
    ) -> None:
        self.discovery = discovery
        self.published_agents = published_agents

    def publish(self, agent_id: str) -> PublishedAgent:
        if self.discovery is None:
            raise UnsupportedOperationError(
                "repo-local agent discovery is not available in this deployment",
                agent_id=agent_id,
            )
        discovered = self._get_discovered_agent(agent_id)
        if discovered.validation_status != AgentValidationStatus.VALID:
            issue_summary = "; ".join(issue.message for issue in discovered.validation_issues) or (
                "agent contract validation failed"
            )
            raise AgentValidationFailedError(agent_id=agent_id, message=issue_summary)

        existing = self.published_agents.get_agent(agent_id)
        published = discovered.to_published(existing=existing)
        self.published_agents.save_agent(published)
        return published

    def unpublish(self, agent_id: str) -> bool:
        deleted = self.published_agents.delete_agent(agent_id)
        if not deleted:
            raise PublishedAgentNotFoundError(agent_id)
        return True

    def _get_discovered_agent(self, agent_id: str) -> DiscoveredAgent:
        if self.discovery is None:
            raise UnsupportedOperationError(
                "repo-local agent discovery is not available in this deployment",
                agent_id=agent_id,
            )
        for agent in self.discovery.list_agents():
            if agent.agent_id == agent_id:
                return agent
        raise AgentValidationFailedError(
            agent_id=agent_id,
            message=(f"agent '{agent_id}' is not available in the current discovery catalog"),
        )


class AgentBootstrapCommands:
    def __init__(
        self,
        published_agents: PublishedAgentRepositoryPort,
        live_agent_markers: LiveAgentMarkerRepositoryPort | None = None,
    ) -> None:
        self.published_agents = published_agents
        self.live_agent_markers = live_agent_markers

    def bootstrap_claude_code(self) -> PublishedAgent:
        ensure_claude_code_starter_runtime_ready()
        if self.live_agent_markers is not None:
            self.live_agent_markers.save_agent_id(CLAUDE_CODE_STARTER_AGENT_ID)
        existing = self.published_agents.get_agent(CLAUDE_CODE_STARTER_AGENT_ID)
        if existing is not None and _is_valid_published_agent(existing):
            return existing

        manifest = claude_code_starter_manifest()
        source_fingerprint = compute_source_fingerprint(
            manifest,
            CLAUDE_CODE_STARTER_ENTRYPOINT,
        )
        published = PublishedAgent(
            manifest=manifest,
            entrypoint=CLAUDE_CODE_STARTER_ENTRYPOINT,
            source_fingerprint=source_fingerprint,
            execution_reference=ExecutionReference.model_validate(
                build_source_execution_reference(
                    agent_id=manifest.agent_id,
                    source_fingerprint=source_fingerprint,
                ).model_dump(mode="json")
            ),
            default_runtime_profile=claude_code_starter_runtime_profile(),
        )
        self.published_agents.save_agent(published)
        return published


class AgentValidationCommands:
    def __init__(
        self,
        discovery: AgentSourceDiscoveryPort | None,
        published_agents: PublishedAgentCatalogPort,
        submission_service: RunSubmissionService,
    ) -> None:
        self.discovery = discovery
        self.published_agents = published_agents
        self.submission_service = submission_service

    def create_run(self, agent_id: str, payload: RunCreateInput) -> RunRecord:
        agent = self._resolve_agent(agent_id)
        if agent.manifest.agent_id == CLAUDE_CODE_STARTER_AGENT_ID:
            ensure_claude_code_starter_runtime_ready()
        return self.submission_service.submit(payload, agent)

    def _resolve_agent(self, agent_id: str) -> PublishedAgent:
        existing = self.published_agents.get_agent(agent_id)
        if existing is not None and _is_valid_published_agent(existing):
            discovered = self._get_discovered_agent(agent_id)
            if discovered is None:
                return existing
            if discovered.validation_status != AgentValidationStatus.VALID:
                issue_summary = (
                    "; ".join(issue.message for issue in discovered.validation_issues)
                    or "agent contract validation failed"
                )
                raise AgentValidationFailedError(agent_id=agent_id, message=issue_summary)
            return discovered.to_published(existing=existing)

        discovered = self._get_discovered_agent(agent_id)
        if discovered is None:
            raise PublishedAgentNotFoundError(agent_id)
        if discovered.validation_status != AgentValidationStatus.VALID:
            issue_summary = "; ".join(issue.message for issue in discovered.validation_issues) or (
                "agent contract validation failed"
            )
            raise AgentValidationFailedError(agent_id=agent_id, message=issue_summary)
        return discovered.to_published(existing=None)

    def _get_discovered_agent(self, agent_id: str) -> DiscoveredAgent | None:
        if self.discovery is None:
            return None
        for agent in self.discovery.list_agents():
            if agent.agent_id == agent_id:
                return agent
        return None
