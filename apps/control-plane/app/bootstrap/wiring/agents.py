from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from app.bootstrap.wiring.infrastructure import InfrastructureBundle
from app.modules.agents.application.use_cases import (
    AgentCatalogQueries,
    AgentDiscoveryQueries,
    AgentPublicationCommands,
)


@dataclass(frozen=True)
class AgentModuleBundle:
    agent_exists: Callable[[str], bool]
    agent_catalog_queries: AgentCatalogQueries
    agent_discovery_queries: AgentDiscoveryQueries
    agent_publication_commands: AgentPublicationCommands


def build_agent_module(infra: InfrastructureBundle) -> AgentModuleBundle:
    def agent_exists(agent_id: str) -> bool:
        return infra.runnable_agent_catalog.get_agent(agent_id) is not None

    agent_catalog_queries = AgentCatalogQueries(runnable_catalog=infra.runnable_agent_catalog)
    agent_discovery_queries = AgentDiscoveryQueries(
        discovery=infra.agent_discovery,
        published_agents=infra.published_agent_repository,
    )
    agent_publication_commands = AgentPublicationCommands(
        discovery=infra.agent_discovery,
        published_agents=infra.published_agent_repository,
        artifact_builder=infra.artifact_builder,
    )

    return AgentModuleBundle(
        agent_exists=agent_exists,
        agent_catalog_queries=agent_catalog_queries,
        agent_discovery_queries=agent_discovery_queries,
        agent_publication_commands=agent_publication_commands,
    )
