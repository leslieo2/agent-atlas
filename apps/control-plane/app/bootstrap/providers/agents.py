from __future__ import annotations

from app.bootstrap.container import get_container
from app.modules.agents.application.use_cases import (
    AgentIntakeCommands,
    AgentValidationCommands,
    PublishedAgentCatalogQueries,
)


def get_published_agent_catalog_queries() -> PublishedAgentCatalogQueries:
    return get_container().agents.published_agent_catalog_queries


def get_agent_intake_commands() -> AgentIntakeCommands:
    return get_container().agents.agent_intake_commands


def get_agent_validation_commands() -> AgentValidationCommands:
    return get_container().agents.agent_validation_commands
