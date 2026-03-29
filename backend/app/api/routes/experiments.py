from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.bootstrap.providers.experiments import get_experiment_commands, get_experiment_queries
from app.core.errors import AppError
from app.modules.experiments.application.use_cases import ExperimentCommands, ExperimentQueries
from app.modules.experiments.contracts.schemas import (
    ExperimentCompareResponse,
    ExperimentCreateRequest,
    ExperimentResponse,
    ExperimentRunResponse,
    RunEvaluationPatchRequest,
)

router = APIRouter(prefix="/experiments", tags=["experiments"])


@router.get("", response_model=list[ExperimentResponse])
def list_experiments(
    queries: Annotated[ExperimentQueries, Depends(get_experiment_queries)],
) -> list[ExperimentResponse]:
    return [ExperimentResponse.from_domain(item) for item in queries.list()]


@router.post("", response_model=ExperimentResponse, status_code=status.HTTP_201_CREATED)
def create_experiment(
    payload: ExperimentCreateRequest,
    commands: Annotated[ExperimentCommands, Depends(get_experiment_commands)],
) -> ExperimentResponse:
    try:
        return ExperimentResponse.from_domain(commands.create(payload.to_domain()))
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.to_detail()) from exc


@router.get("/compare", response_model=ExperimentCompareResponse)
def compare_experiments(
    baseline_experiment_id: Annotated[str, Query()],
    candidate_experiment_id: Annotated[str, Query()],
    queries: Annotated[ExperimentQueries, Depends(get_experiment_queries)],
) -> ExperimentCompareResponse:
    try:
        result = queries.compare(baseline_experiment_id, candidate_experiment_id)
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.to_detail()) from exc
    return ExperimentCompareResponse.from_domain(result)


@router.get("/{experiment_id}", response_model=ExperimentResponse)
def get_experiment(
    experiment_id: str,
    queries: Annotated[ExperimentQueries, Depends(get_experiment_queries)],
) -> ExperimentResponse:
    experiment = queries.get(experiment_id)
    if experiment is None:
        raise HTTPException(status_code=404, detail="experiment not found")
    return ExperimentResponse.from_domain(experiment)


@router.post("/{experiment_id}/start", response_model=ExperimentResponse)
def start_experiment(
    experiment_id: str,
    commands: Annotated[ExperimentCommands, Depends(get_experiment_commands)],
) -> ExperimentResponse:
    try:
        return ExperimentResponse.from_domain(commands.start(experiment_id))
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.to_detail()) from exc


@router.post("/{experiment_id}/cancel", response_model=ExperimentResponse)
def cancel_experiment(
    experiment_id: str,
    commands: Annotated[ExperimentCommands, Depends(get_experiment_commands)],
) -> ExperimentResponse:
    try:
        return ExperimentResponse.from_domain(commands.cancel(experiment_id))
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.to_detail()) from exc


@router.get("/{experiment_id}/runs", response_model=list[ExperimentRunResponse])
def list_experiment_runs(
    experiment_id: str,
    queries: Annotated[ExperimentQueries, Depends(get_experiment_queries)],
) -> list[ExperimentRunResponse]:
    try:
        return [
            ExperimentRunResponse.from_domain(item) for item in queries.list_runs(experiment_id)
        ]
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.to_detail()) from exc


@router.patch("/{experiment_id}/runs/{run_id}", response_model=ExperimentRunResponse)
def patch_experiment_run(
    experiment_id: str,
    run_id: str,
    payload: RunEvaluationPatchRequest,
    commands: Annotated[ExperimentCommands, Depends(get_experiment_commands)],
    queries: Annotated[ExperimentQueries, Depends(get_experiment_queries)],
) -> ExperimentRunResponse:
    try:
        commands.patch_run_evaluation(experiment_id, run_id, payload.to_domain())
        run_details = queries.list_runs(experiment_id)
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.to_detail()) from exc
    for detail in run_details:
        if str(detail.run_id) == run_id:
            return ExperimentRunResponse.from_domain(detail)
    raise HTTPException(status_code=404, detail="run evaluation not found")
