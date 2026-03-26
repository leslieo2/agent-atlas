from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.bootstrap.container import get_agent_queries
from app.core.errors import AppError
from app.modules.agents.api.schemas import AgentDescriptorResponse
from app.modules.agents.application.use_cases import AgentQueries

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("", response_model=list[AgentDescriptorResponse])
def list_agents(
    queries: Annotated[AgentQueries, Depends(get_agent_queries)],
) -> list[AgentDescriptorResponse]:
    try:
        return [AgentDescriptorResponse.from_domain(agent) for agent in queries.list_agents()]
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.to_detail()) from exc
