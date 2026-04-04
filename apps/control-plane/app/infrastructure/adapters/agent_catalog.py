from __future__ import annotations

from typing import Protocol

from app.modules.agents.application.ports import (
    LiveAgentMarkerRepositoryPort,
    PublishedAgentRepositoryPort,
)
from app.modules.agents.domain.models import (
    AgentModuleSource,
    AgentPublishState,
    AgentValidationIssue,
    AgentValidationStatus,
    DiscoveredAgent,
    PublishedAgent,
)
from app.modules.agents.domain.starter_assets import (
    CLAUDE_CODE_STARTER_AGENT_ID,
    CLAUDE_CODE_STARTER_ENTRYPOINT,
    claude_code_starter_manifest,
    claude_code_starter_runtime_profile,
)
from app.modules.shared.domain.models import ExecutionReferenceMetadata


class AgentSourceCatalog(Protocol):
    def list_sources(self) -> list[AgentModuleSource]: ...


class AgentContractValidator(Protocol):
    def discover(self, source: AgentModuleSource) -> DiscoveredAgent: ...


class StaticAgentDiscovery:
    def __init__(
        self,
        source_catalog: AgentSourceCatalog,
        validator: AgentContractValidator,
    ) -> None:
        self.source_catalog = source_catalog
        self.validator = validator

    def list_agents(self) -> list[DiscoveredAgent]:
        discovered = [
            self.validator.discover(source) for source in self.source_catalog.list_sources()
        ]
        duplicates: dict[str, list[int]] = {}
        for index, agent in enumerate(discovered):
            duplicates.setdefault(agent.agent_id, []).append(index)

        for agent_id, indexes in duplicates.items():
            if len(indexes) < 2:
                continue
            for index in indexes:
                current = discovered[index]
                issues = list(current.validation_issues)
                issues.append(
                    AgentValidationIssue(
                        code="duplicate_agent_id",
                        message=f"agent_id '{agent_id}' is declared by multiple sources",
                    )
                )
                discovered[index] = current.model_copy(
                    update={
                        "validation_status": AgentValidationStatus.INVALID,
                        "validation_issues": issues,
                    }
                )

        return sorted(discovered, key=lambda agent: agent.agent_id)


class StatePublishedAgentCatalog:
    def __init__(
        self,
        published_agents: PublishedAgentRepositoryPort,
    ) -> None:
        self.published_agents = published_agents

    def list_agents(self) -> list[PublishedAgent]:
        eligible_by_id = self._eligible_published_by_id()
        return sorted(
            [
                agent
                for agent in self.published_agents.list_agents()
                if agent.agent_id in eligible_by_id
            ],
            key=lambda agent: agent.agent_id,
        )

    def get_agent(self, agent_id: str) -> PublishedAgent | None:
        return self._eligible_published_by_id().get(agent_id)

    def _eligible_published_by_id(self) -> dict[str, PublishedAgent]:
        eligible: dict[str, PublishedAgent] = {}
        for persisted_agent in self.published_agents.list_agents():
            try:
                persisted_agent.source_fingerprint_or_raise()
                persisted_agent.execution_reference_or_raise()
            except ValueError:
                continue
            eligible[persisted_agent.agent_id] = persisted_agent
        return eligible


class StateBootstrapAgentDiscovery:
    def __init__(
        self,
        markers: LiveAgentMarkerRepositoryPort,
        published_agents: PublishedAgentRepositoryPort,
    ) -> None:
        self.markers = markers
        self.published_agents = published_agents

    def list_agents(self) -> list[DiscoveredAgent]:
        published = self.published_agents.get_agent(CLAUDE_CODE_STARTER_AGENT_ID)
        should_surface = (
            CLAUDE_CODE_STARTER_AGENT_ID in set(self.markers.list_agent_ids())
            or published is not None
        )
        if not should_surface:
            return []
        if published is not None:
            try:
                published.execution_reference_or_raise()
                published.source_fingerprint_or_raise()
            except ValueError:
                pass
            else:
                return [
                    DiscoveredAgent(
                        manifest=published.manifest.model_copy(deep=True),
                        entrypoint=published.entrypoint,
                        publish_state=AgentPublishState.PUBLISHED,
                        validation_status=AgentValidationStatus.VALID,
                        validation_issues=[],
                        published_at=published.published_at,
                        execution_reference=ExecutionReferenceMetadata.model_validate(
                            published.execution_reference.model_dump(mode="json")
                        ),
                        default_runtime_profile=published.default_runtime_profile.model_copy(
                            deep=True
                        ),
                    )
                ]
        return [
            DiscoveredAgent(
                manifest=claude_code_starter_manifest(),
                entrypoint=CLAUDE_CODE_STARTER_ENTRYPOINT,
                validation_status=AgentValidationStatus.VALID,
                validation_issues=[],
                default_runtime_profile=claude_code_starter_runtime_profile(),
            )
        ]
