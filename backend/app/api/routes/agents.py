from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.bootstrap.container import (
    get_agent_catalog_queries,
    get_agent_discovery_queries,
    get_agent_publication_commands,
)
from app.core.errors import AppError
from app.modules.agents.api.schemas import (
    AgentDescriptorResponse,
    AgentPublicationResponse,
    DiscoveredAgentResponse,
)
from app.modules.agents.application.use_cases import (
    AgentCatalogQueries,
    AgentDiscoveryQueries,
    AgentPublicationCommands,
)

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("", response_model=list[AgentDescriptorResponse])
def list_agents(
    queries: Annotated[AgentCatalogQueries, Depends(get_agent_catalog_queries)],
) -> list[AgentDescriptorResponse]:
    try:
        return [AgentDescriptorResponse.from_domain(agent) for agent in queries.list_agents()]
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.to_detail()) from exc


@router.get("/discovered", response_model=list[DiscoveredAgentResponse])
def list_discovered_agents(
    queries: Annotated[AgentDiscoveryQueries, Depends(get_agent_discovery_queries)],
) -> list[DiscoveredAgentResponse]:
    try:
        return [DiscoveredAgentResponse.from_domain(agent) for agent in queries.list_agents()]
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.to_detail()) from exc


@router.post("/{agent_id}/publish", response_model=AgentDescriptorResponse)
def publish_agent(
    agent_id: str,
    commands: Annotated[AgentPublicationCommands, Depends(get_agent_publication_commands)],
) -> AgentDescriptorResponse:
    try:
        return AgentDescriptorResponse.from_domain(commands.publish(agent_id))
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.to_detail()) from exc


@router.post("/{agent_id}/unpublish", response_model=AgentPublicationResponse)
def unpublish_agent(
    agent_id: str,
    commands: Annotated[AgentPublicationCommands, Depends(get_agent_publication_commands)],
) -> AgentPublicationResponse:
    try:
        commands.unpublish(agent_id)
        return AgentPublicationResponse(agent_id=agent_id, published=False)
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.to_detail()) from exc
