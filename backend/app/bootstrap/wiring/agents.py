from __future__ import annotations

from dataclasses import dataclass

from app.bootstrap.wiring.infrastructure import InfrastructureBundle
from app.infrastructure.adapters.evals import RunnableAgentLookupAdapter
from app.modules.agents.application.use_cases import (
    AgentCatalogQueries,
    AgentDiscoveryQueries,
    AgentPublicationCommands,
)


@dataclass(frozen=True)
class AgentModuleBundle:
    agent_lookup: RunnableAgentLookupAdapter
    agent_catalog_queries: AgentCatalogQueries
    agent_discovery_queries: AgentDiscoveryQueries
    agent_publication_commands: AgentPublicationCommands


def build_agent_module(infra: InfrastructureBundle) -> AgentModuleBundle:
    agent_lookup = RunnableAgentLookupAdapter(agent_catalog=infra.runnable_agent_catalog)
    agent_catalog_queries = AgentCatalogQueries(runnable_catalog=infra.runnable_agent_catalog)
    agent_discovery_queries = AgentDiscoveryQueries(
        discovery=infra.agent_discovery,
        published_agents=infra.published_agent_repository,
    )
    agent_publication_commands = AgentPublicationCommands(
        discovery=infra.agent_discovery,
        published_agents=infra.published_agent_repository,
    )

    return AgentModuleBundle(
        agent_lookup=agent_lookup,
        agent_catalog_queries=agent_catalog_queries,
        agent_discovery_queries=agent_discovery_queries,
        agent_publication_commands=agent_publication_commands,
    )
