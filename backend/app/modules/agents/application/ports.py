from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from pydantic import SecretStr

from app.modules.agents.domain.models import (
    AgentBuildContext,
    AgentModuleSource,
    DiscoveredAgent,
    PublishedAgent,
)
from app.modules.shared.domain.models import ProvenanceMetadata

if TYPE_CHECKING:
    from app.modules.runs.application.results import PublishedRunExecutionResult
    from app.modules.runs.domain.models import RunSpec


class AgentSourceDiscoveryPort(Protocol):
    def list_agents(self) -> list[DiscoveredAgent]: ...


class PublishedAgentRepositoryPort(Protocol):
    def list_agents(self) -> list[PublishedAgent]: ...

    def get_agent(self, agent_id: str) -> PublishedAgent | None: ...

    def save_agent(self, agent: PublishedAgent) -> None: ...

    def delete_agent(self, agent_id: str) -> bool: ...


class RunnableAgentCatalogPort(Protocol):
    def list_agents(self) -> list[PublishedAgent]: ...

    def get_agent(self, agent_id: str) -> PublishedAgent | None: ...


class FrameworkRegistryPort(Protocol):
    def discover(self, source: AgentModuleSource) -> DiscoveredAgent: ...

    def build_agent(
        self, *, published_agent: PublishedAgent, context: AgentBuildContext
    ) -> object: ...

    def execute_published(
        self,
        *,
        api_key: SecretStr | None,
        payload: RunSpec,
        context: AgentBuildContext,
    ) -> PublishedRunExecutionResult: ...


class ArtifactBuilderPort(Protocol):
    def build(self, published_agent: PublishedAgent) -> ProvenanceMetadata: ...
