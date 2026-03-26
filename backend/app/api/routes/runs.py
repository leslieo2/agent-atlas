from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.bootstrap.container import get_run_commands, get_run_queries
from app.core.errors import AppError
from app.modules.runs.api.schemas import (
    RunCreateRequest,
    RunResponse,
    TerminateRunResponse,
    TrajectoryStepResponse,
)
from app.modules.runs.application.use_cases import RunCommands, RunQueries
from app.modules.shared.domain.enums import RunStatus
from app.modules.traces.api.schemas import TraceSpanResponse

router = APIRouter(prefix="/runs", tags=["runs"])


@router.get("", response_model=list[RunResponse])
def list_runs(
    queries: Annotated[RunQueries, Depends(get_run_queries)],
    status: RunStatus | None = None,
    project: str | None = None,
    dataset: str | None = None,
    agent_id: str | None = None,
    model: str | None = None,
    tag: str | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
) -> list[RunResponse]:
    runs = queries.list_runs(
        status,
        project,
        dataset,
        agent_id,
        model,
        tag,
        created_from,
        created_to,
    )
    return [RunResponse.from_domain(run) for run in runs]


@router.post("", response_model=RunResponse, status_code=status.HTTP_201_CREATED)
def create_run(
    payload: RunCreateRequest,
    commands: Annotated[RunCommands, Depends(get_run_commands)],
) -> RunResponse:
    try:
        run = commands.create_run(payload.to_domain())
        return RunResponse.from_domain(run)
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.to_detail()) from exc


@router.get("/{run_id}", response_model=RunResponse)
def get_run(
    run_id: str,
    queries: Annotated[RunQueries, Depends(get_run_queries)],
) -> RunResponse:
    run = queries.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="run not found")
    return RunResponse.from_domain(run)


@router.post(
    "/{run_id}/terminate",
    response_model=TerminateRunResponse,
    status_code=status.HTTP_200_OK,
)
def terminate_run(
    run_id: str,
    commands: Annotated[RunCommands, Depends(get_run_commands)],
) -> TerminateRunResponse:
    run = commands.terminate(run_id)
    if not run:
        raise HTTPException(status_code=400, detail="run not running or not found")
    return TerminateRunResponse(
        run_id=run.run_id,
        terminated=True,
        status=run.status,
        termination_reason=run.termination_reason,
    )


@router.get("/{run_id}/trajectory", response_model=list[TrajectoryStepResponse])
def get_trajectory(
    run_id: str,
    queries: Annotated[RunQueries, Depends(get_run_queries)],
) -> list[TrajectoryStepResponse]:
    trajectory = queries.get_trajectory(run_id)
    return [TrajectoryStepResponse.from_domain(step) for step in trajectory]


@router.get("/{run_id}/traces", response_model=list[TraceSpanResponse])
def get_trace(
    run_id: str,
    queries: Annotated[RunQueries, Depends(get_run_queries)],
) -> list[TraceSpanResponse]:
    traces = queries.get_traces(run_id)
    return [TraceSpanResponse.from_domain(trace) for trace in traces]
