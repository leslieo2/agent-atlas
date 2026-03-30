from __future__ import annotations

from app.bootstrap.container import get_container
from app.modules.agents.application.use_cases import (
    AgentCatalogQueries,
    AgentDiscoveryQueries,
    AgentPublicationCommands,
)


def get_agent_catalog_queries() -> AgentCatalogQueries:
    return get_container().agents.agent_catalog_queries


def get_agent_discovery_queries() -> AgentDiscoveryQueries:
    return get_container().agents.agent_discovery_queries


def get_agent_publication_commands() -> AgentPublicationCommands:
    return get_container().agents.agent_publication_commands
