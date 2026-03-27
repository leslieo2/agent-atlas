from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.bootstrap.container import get_eval_commands, get_eval_queries
from app.core.errors import AppError
from app.modules.evals.api.schemas import (
    EvalJobCreateRequest,
    EvalJobResponse,
    EvalSampleResultResponse,
)
from app.modules.evals.application.use_cases import EvalJobCommands, EvalJobQueries

router = APIRouter(prefix="/eval-jobs", tags=["eval-jobs"])


@router.post("", response_model=EvalJobResponse, status_code=status.HTTP_201_CREATED)
def create_eval_job(
    payload: EvalJobCreateRequest,
    commands: Annotated[EvalJobCommands, Depends(get_eval_commands)],
) -> EvalJobResponse:
    try:
        job = commands.create_job(payload.to_domain())
        return EvalJobResponse.from_domain(job)
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.to_detail()) from exc


@router.get("", response_model=list[EvalJobResponse])
def list_eval_jobs(
    queries: Annotated[EvalJobQueries, Depends(get_eval_queries)],
) -> list[EvalJobResponse]:
    return [EvalJobResponse.from_domain(job) for job in queries.list_jobs()]


@router.get("/{eval_job_id}", response_model=EvalJobResponse)
def get_eval_job(
    eval_job_id: str,
    queries: Annotated[EvalJobQueries, Depends(get_eval_queries)],
) -> EvalJobResponse:
    job = queries.get_job(eval_job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="eval job not found")
    return EvalJobResponse.from_domain(job)


@router.get("/{eval_job_id}/samples", response_model=list[EvalSampleResultResponse])
def list_eval_job_samples(
    eval_job_id: str,
    queries: Annotated[EvalJobQueries, Depends(get_eval_queries)],
) -> list[EvalSampleResultResponse]:
    if queries.get_job(eval_job_id) is None:
        raise HTTPException(status_code=404, detail="eval job not found")
    return [
        EvalSampleResultResponse.from_domain(result) for result in queries.list_samples(eval_job_id)
    ]
