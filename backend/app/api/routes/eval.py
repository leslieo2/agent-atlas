from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.models.schemas import EvalJob, EvalJobCreate
from app.services.eval_service import eval_service

router = APIRouter(prefix="/eval-jobs", tags=["eval"])


@router.post("", response_model=EvalJob)
def create_eval_job(payload: EvalJobCreate) -> EvalJob:
    if not payload.run_ids:
        raise HTTPException(status_code=400, detail="run_ids cannot be empty")
    return eval_service.create_job(payload)


@router.get("/{job_id}", response_model=EvalJob)
def get_eval_job(job_id: str) -> EvalJob:
    job = eval_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    return job
