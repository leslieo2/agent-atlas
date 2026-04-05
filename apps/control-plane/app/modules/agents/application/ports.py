from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from agent_atlas_contracts.execution import RunnerRunSpec
from pydantic import SecretStr

from app.modules.agents.domain.models import (
    AgentBuildContext,
    AgentModuleSource,
    AgentValidationRecord,
    DiscoveredAgent,
    PublishedAgent,
)

if TYPE_CHECKING:
    from app.execution.application.results import PublishedRunExecutionResult


class PublishedAgentRepositoryPort(Protocol):
    def list_agents(self) -> list[PublishedAgent]: ...

    def get_agent(self, agent_id: str) -> PublishedAgent | None: ...

    def save_agent(self, agent: PublishedAgent) -> None: ...

    def delete_agent(self, agent_id: str) -> bool: ...


class PublishedAgentCatalogPort(Protocol):
    def list_agents(self) -> list[PublishedAgent]: ...

    def get_agent(self, agent_id: str) -> PublishedAgent | None: ...


class AgentValidationRecordPort(Protocol):
    def list_records(self) -> list[AgentValidationRecord]: ...


class FrameworkRegistryPort(Protocol):
    def discover(self, source: AgentModuleSource) -> DiscoveredAgent: ...

    def build_agent(
        self, *, published_agent: PublishedAgent, context: AgentBuildContext
    ) -> object: ...


class PublishedAgentExecutionPort(Protocol):
    def published_agent_from_payload(self, payload: RunnerRunSpec) -> PublishedAgent: ...

    def execute_published(
        self,
        *,
        api_key: SecretStr | None,
        payload: RunnerRunSpec,
        context: AgentBuildContext,
    ) -> PublishedRunExecutionResult: ...
