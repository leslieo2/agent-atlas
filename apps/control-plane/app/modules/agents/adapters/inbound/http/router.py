from __future__ import annotations

from typing import Annotated, Protocol

from app.bootstrap.providers.agents import (
    get_agent_bootstrap_commands,
    get_agent_validation_commands,
    get_published_agent_catalog_queries,
)
from app.core.errors import AppError
from app.modules.agents.adapters.inbound.http.schemas import (
    AgentDescriptorResponse,
    AgentValidationRunStartRequest,
)
from app.modules.agents.application.use_cases import (
    AgentBootstrapCommands,
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
