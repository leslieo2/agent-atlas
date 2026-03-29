from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.bootstrap.providers.evals import get_eval_commands, get_eval_queries
from app.core.errors import AppError
from app.modules.evals.application.use_cases import EvalJobCommands, EvalJobQueries
from app.modules.evals.contracts.schemas import (
    EvalCompareResponse,
    EvalJobCreateRequest,
    EvalJobResponse,
    EvalSampleDetailResponse,
    EvalSamplePatchRequest,
)

router = APIRouter(prefix="/eval-jobs", tags=["eval-jobs"])


@router.get("/compare", response_model=EvalCompareResponse)
def compare_eval_jobs(
    baseline_eval_job_id: Annotated[str, Query()],
    candidate_eval_job_id: Annotated[str, Query()],
    queries: Annotated[EvalJobQueries, Depends(get_eval_queries)],
) -> EvalCompareResponse:
    try:
        result = queries.compare_jobs(baseline_eval_job_id, candidate_eval_job_id)
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.to_detail()) from exc
    return EvalCompareResponse.from_domain(result)


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


@router.get("/{eval_job_id}/samples", response_model=list[EvalSampleDetailResponse])
def list_eval_job_samples(
    eval_job_id: str,
    queries: Annotated[EvalJobQueries, Depends(get_eval_queries)],
) -> list[EvalSampleDetailResponse]:
    if queries.get_job(eval_job_id) is None:
        raise HTTPException(status_code=404, detail="eval job not found")
    return [
        EvalSampleDetailResponse.from_domain(result) for result in queries.list_samples(eval_job_id)
    ]


@router.get("/{eval_job_id}/samples/{dataset_sample_id}", response_model=EvalSampleDetailResponse)
def get_eval_job_sample(
    eval_job_id: str,
    dataset_sample_id: str,
    queries: Annotated[EvalJobQueries, Depends(get_eval_queries)],
) -> EvalSampleDetailResponse:
    if queries.get_job(eval_job_id) is None:
        raise HTTPException(status_code=404, detail="eval job not found")
    result = queries.get_sample(eval_job_id, dataset_sample_id)
    if result is None:
        raise HTTPException(status_code=404, detail="eval sample not found")
    return EvalSampleDetailResponse.from_domain(result)


@router.patch("/{eval_job_id}/samples/{dataset_sample_id}", response_model=EvalSampleDetailResponse)
def patch_eval_job_sample(
    eval_job_id: str,
    dataset_sample_id: str,
    payload: EvalSamplePatchRequest,
    commands: Annotated[EvalJobCommands, Depends(get_eval_commands)],
) -> EvalSampleDetailResponse:
    try:
        result = commands.patch_sample(eval_job_id, dataset_sample_id, payload.to_domain())
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.to_detail()) from exc
    return EvalSampleDetailResponse.from_domain(result)
