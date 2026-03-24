from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, status

from app.models.schemas import RunCreateRequest, RunRecord, RunStatus
from app.services.orchestrator import orchestrator

router = APIRouter(prefix="/runs", tags=["runs"])


@router.get("", response_model=list[RunRecord])
def list_runs(
    status: RunStatus | None = None,
    project: str | None = None,
    dataset: str | None = None,
    model: str | None = None,
    tag: str | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
) -> list[RunRecord]:
    return orchestrator.list_runs(status, project, dataset, model, tag, created_from, created_to)


@router.post("", response_model=RunRecord, status_code=status.HTTP_201_CREATED)
def create_run(payload: RunCreateRequest) -> RunRecord:
    return orchestrator.create_run(payload)


@router.get("/{run_id}", response_model=RunRecord)
def get_run(run_id: str) -> RunRecord:
    run = orchestrator.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="run not found")
    return run


@router.post("/{run_id}/terminate", status_code=status.HTTP_200_OK)
def terminate_run(run_id: str) -> dict[str, Any]:
    ok = orchestrator.terminate(run_id)
    if not ok:
        raise HTTPException(status_code=400, detail="run not running or not found")
    return {"run_id": run_id, "terminated": True}


@router.get("/{run_id}/trajectory")
def get_trajectory(run_id: str) -> list[dict]:
    trajectory = orchestrator.get_trajectory(run_id)
    return [step.model_dump() for step in trajectory]


@router.get("/{run_id}/traces")
def get_trace(run_id: str) -> list[dict]:
    traces = orchestrator.get_traces(run_id)
    return [trace.model_dump() for trace in traces]
