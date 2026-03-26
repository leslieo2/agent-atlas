from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.bootstrap.container import get_eval_job_commands, get_eval_job_queries
from app.core.errors import AppError
from app.modules.evals.api.schemas import EvalJobCreate, EvalJobResponse
from app.modules.evals.application.use_cases import EvalJobCommands, EvalJobQueries

router = APIRouter(prefix="/eval-jobs", tags=["eval"])


@router.post("", response_model=EvalJobResponse)
def create_eval_job(
    payload: EvalJobCreate,
    commands: Annotated[EvalJobCommands, Depends(get_eval_job_commands)],
) -> EvalJobResponse:
    if not payload.run_ids:
        raise HTTPException(status_code=400, detail="run_ids cannot be empty")
    try:
        job = commands.create_job(payload.to_domain())
        return EvalJobResponse.from_domain(job)
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.to_detail()) from exc


@router.get("/{job_id}", response_model=EvalJobResponse)
def get_eval_job(
    job_id: str,
    queries: Annotated[EvalJobQueries, Depends(get_eval_job_queries)],
) -> EvalJobResponse:
    job = queries.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    return EvalJobResponse.from_domain(job)
