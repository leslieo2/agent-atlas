from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from agent_atlas_contracts.execution import RunnerRunSpec
from agent_atlas_contracts.runtime import AgentBuildContext
from agent_atlas_contracts.runtime import PublishedAgent as ContractPublishedAgentSnapshot
from pydantic import SecretStr

from app.modules.agents.domain.models import (
    AgentModuleSource,
    AgentValidationRecord,
    AgentValidationRun,
    AgentValidationRunCreateInput,
    DiscoveredAgent,
    GovernedPublishedAgent,
)

if TYPE_CHECKING:
    from app.execution.application.results import PublishedRunExecutionResult


class PublishedAgentRepositoryPort(Protocol):
    def list_agents(self) -> list[GovernedPublishedAgent]: ...

    def get_agent(self, agent_id: str) -> GovernedPublishedAgent | None: ...

    def save_agent(self, agent: GovernedPublishedAgent) -> None: ...

    def delete_agent(self, agent_id: str) -> bool: ...


class PublishedAgentCatalogPort(Protocol):
    def list_agents(self) -> list[GovernedPublishedAgent]: ...

    def get_agent(self, agent_id: str) -> GovernedPublishedAgent | None: ...


class AgentValidationRecordPort(Protocol):
    def list_records(self) -> list[AgentValidationRecord]: ...


class AgentValidationSubmissionPort(Protocol):
    def submit_validation(
        self,
        payload: AgentValidationRunCreateInput,
        agent: GovernedPublishedAgent,
    ) -> AgentValidationRun: ...


class FrameworkRegistryPort(Protocol):
    def discover(self, source: AgentModuleSource) -> DiscoveredAgent: ...

    def build_agent(
        self,
        *,
        published_agent: ContractPublishedAgentSnapshot,
        context: AgentBuildContext,
    ) -> object: ...


class PublishedAgentExecutionPort(Protocol):
    def published_agent_from_payload(
        self,
        payload: RunnerRunSpec,
    ) -> ContractPublishedAgentSnapshot: ...

    def execute_published(
        self,
        *,
        api_key: SecretStr | None,
        payload: RunnerRunSpec,
        context: AgentBuildContext,
    ) -> PublishedRunExecutionResult: ...
