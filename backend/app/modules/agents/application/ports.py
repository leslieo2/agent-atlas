from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from pydantic import SecretStr

from app.execution_plane.contracts import RunnerRunSpec
from app.modules.agents.domain.models import (
    AgentBuildContext,
    AgentModuleSource,
    DiscoveredAgent,
    PublishedAgent,
)
from app.modules.shared.domain.models import RuntimeArtifactBuildResult

if TYPE_CHECKING:
    from app.modules.runs.application.results import PublishedRunExecutionResult


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
        payload: RunnerRunSpec,
        context: AgentBuildContext,
    ) -> PublishedRunExecutionResult: ...


class ArtifactBuilderPort(Protocol):
    def build(self, published_agent: PublishedAgent) -> RuntimeArtifactBuildResult: ...
