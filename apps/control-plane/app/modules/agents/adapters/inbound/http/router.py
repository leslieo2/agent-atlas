from __future__ import annotations

from typing import Annotated, Protocol

from app.bootstrap.providers.agents import (
    get_agent_bootstrap_commands,
    get_agent_discovery_queries,
    get_agent_publication_commands,
    get_agent_validation_commands,
    get_published_agent_catalog_queries,
)
from app.core.errors import AppError
from app.modules.agents.adapters.inbound.http.schemas import (
    AgentDescriptorResponse,
    AgentPublicationResponse,
    AgentValidationRunStartRequest,
    DiscoveredAgentResponse,
)
from app.modules.agents.application.use_cases import (
    AgentBootstrapCommands,
    AgentDiscoveryQueries,
    AgentPublicationCommands,
    AgentValidationCommands,
    PublishedAgentCatalogQueries,
)
from app.modules.runs.adapters.inbound.http.schemas import RunResponse
from app.modules.runs.domain.models import RunCreateInput, RunRecord
from fastapi import APIRouter, Depends, HTTPException

router = APIRouter(prefix="/agents", tags=["agents"])


class ValidationRunCommands(Protocol):
    def create_run(self, agent_id: str, payload: RunCreateInput) -> RunRecord: ...


@router.get("/published", response_model=list[AgentDescriptorResponse])
def list_published_agents(
    queries: Annotated[PublishedAgentCatalogQueries, Depends(get_published_agent_catalog_queries)],
) -> list[AgentDescriptorResponse]:
    try:
        return [AgentDescriptorResponse.from_domain(agent) for agent in queries.list_agents()]
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.to_detail()) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=500,
            detail={"code": "agent_descriptor_invalid", "message": str(exc)},
        ) from exc


@router.get("/discovered", response_model=list[DiscoveredAgentResponse])
def list_discovered_agents(
    queries: Annotated[AgentDiscoveryQueries, Depends(get_agent_discovery_queries)],
) -> list[DiscoveredAgentResponse]:
    try:
        return [DiscoveredAgentResponse.from_domain(agent) for agent in queries.list_agents()]
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.to_detail()) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=500,
            detail={"code": "agent_descriptor_invalid", "message": str(exc)},
        ) from exc


@router.post("/{agent_id}/publish", response_model=AgentDescriptorResponse)
def publish_agent(
    agent_id: str,
    commands: Annotated[AgentPublicationCommands, Depends(get_agent_publication_commands)],
) -> AgentDescriptorResponse:
    try:
        return AgentDescriptorResponse.from_domain(commands.publish(agent_id))
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.to_detail()) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=500,
            detail={"code": "agent_descriptor_invalid", "message": str(exc)},
        ) from exc


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


@router.post("/bootstrap/claude-code", response_model=AgentDescriptorResponse)
def bootstrap_claude_code_agent(
    commands: Annotated[AgentBootstrapCommands, Depends(get_agent_bootstrap_commands)],
) -> AgentDescriptorResponse:
    try:
        return AgentDescriptorResponse.from_domain(commands.bootstrap_claude_code())
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.to_detail()) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=500,
            detail={"code": "agent_descriptor_invalid", "message": str(exc)},
        ) from exc


@router.post("/{agent_id}/validation-runs", response_model=RunResponse)
def start_validation_run(
    agent_id: str,
    payload: AgentValidationRunStartRequest,
    commands: Annotated[AgentValidationCommands, Depends(get_agent_validation_commands)],
) -> RunResponse:
    try:
        run = commands.create_run(agent_id, payload.to_domain(agent_id=agent_id))
        return RunResponse.from_domain(run)
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.to_detail()) from exc
