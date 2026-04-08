from __future__ import annotations

from typing import Annotated

from app.bootstrap.providers.agents import (
    get_agent_intake_commands,
    get_agent_validation_commands,
    get_published_agent_catalog_queries,
)
from app.core.errors import AppError
from app.modules.agents.adapters.inbound.http.schemas import (
    AgentDescriptorResponse,
    AgentImportRequest,
    AgentValidationRunStartRequest,
)
from app.modules.agents.application.use_cases import (
    AgentIntakeCommands,
    AgentValidationCommands,
    GovernedAgentIntake,
    PublishedAgentCatalogQueries,
)
from app.modules.agents.domain.reference_assets import (
    CLAUDE_CODE_STARTER_ENTRYPOINT,
    claude_code_starter_execution_binding,
    claude_code_starter_manifest,
    claude_code_starter_runtime_profile,
    ensure_claude_code_starter_runtime_ready,
)
from app.modules.runs.adapters.inbound.http.schemas import RunResponse
from fastapi import APIRouter, Depends, HTTPException

router = APIRouter(prefix="/agents", tags=["agents"])


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


@router.post("/imports", response_model=AgentDescriptorResponse)
def import_agent_source(
    payload: AgentImportRequest,
    commands: Annotated[AgentIntakeCommands, Depends(get_agent_intake_commands)],
) -> AgentDescriptorResponse:
    try:
        return AgentDescriptorResponse.from_domain(
            commands.publish_governed_intake(
                GovernedAgentIntake.for_import(
                    payload.manifest(),
                    entrypoint=payload.entrypoint,
                )
            )
        )
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.to_detail()) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=500,
            detail={"code": "agent_descriptor_invalid", "message": str(exc)},
        ) from exc


@router.post("/starters/claude-code", response_model=AgentDescriptorResponse)
def create_claude_code_starter(
    commands: Annotated[AgentIntakeCommands, Depends(get_agent_intake_commands)],
) -> AgentDescriptorResponse:
    try:
        return AgentDescriptorResponse.from_domain(
            commands.publish_governed_intake(
                GovernedAgentIntake(
                    manifest=claude_code_starter_manifest(),
                    entrypoint=CLAUDE_CODE_STARTER_ENTRYPOINT,
                    default_runtime_profile=claude_code_starter_runtime_profile(),
                    execution_binding=claude_code_starter_execution_binding(),
                    prepare_runtime=ensure_claude_code_starter_runtime_ready,
                )
            )
        )
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
        run = commands.create_run(agent_id, payload.to_domain())
        return RunResponse.model_validate(run.model_dump(mode="json"))
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.to_detail()) from exc
