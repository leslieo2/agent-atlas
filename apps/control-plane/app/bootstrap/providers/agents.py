from __future__ import annotations

from app.bootstrap.container import get_container
from app.modules.agents.application.use_cases import (
    AgentBootstrapCommands,
    AgentDiscoveryQueries,
    AgentPublicationCommands,
    PublishedAgentCatalogQueries,
)


def get_agent_discovery_queries() -> AgentDiscoveryQueries:
    return get_container().agents.agent_discovery_queries


def get_published_agent_catalog_queries() -> PublishedAgentCatalogQueries:
    return get_container().agents.published_agent_catalog_queries


def get_agent_publication_commands() -> AgentPublicationCommands:
    return get_container().agents.agent_publication_commands


def get_agent_bootstrap_commands() -> AgentBootstrapCommands:
    return get_container().agents.agent_bootstrap_commands
