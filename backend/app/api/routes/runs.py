from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.bootstrap.providers.runs import get_run_queries
from app.modules.runs.application.use_cases import RunQueries
from app.modules.runs.contracts.schemas import RunResponse

router = APIRouter(prefix="/runs", tags=["runs"])


@router.get("/{run_id}", response_model=RunResponse)
def get_run(
    run_id: str,
    queries: Annotated[RunQueries, Depends(get_run_queries)],
) -> RunResponse:
    run = queries.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    return RunResponse.from_domain(run)
