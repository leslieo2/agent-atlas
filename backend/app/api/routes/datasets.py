from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.bootstrap.providers.datasets import get_dataset_commands, get_dataset_queries
from app.modules.datasets.application.use_cases import DatasetCommands, DatasetQueries
from app.modules.datasets.contracts.schemas import (
    DatasetCreate,
    DatasetResponse,
    DatasetVersionCreate,
    DatasetVersionResponse,
)

router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.get("", response_model=list[DatasetResponse])
def list_datasets(
    queries: Annotated[DatasetQueries, Depends(get_dataset_queries)],
) -> list[DatasetResponse]:
    return [DatasetResponse.from_domain(dataset) for dataset in queries.list()]


@router.get("/{dataset_name}", response_model=DatasetResponse)
def get_dataset(
    dataset_name: str,
    queries: Annotated[DatasetQueries, Depends(get_dataset_queries)],
) -> DatasetResponse:
    dataset = queries.get(dataset_name)
    if dataset is None:
        raise HTTPException(status_code=404, detail="dataset not found")
    return DatasetResponse.from_domain(dataset)


@router.post("", response_model=DatasetResponse)
def create_dataset(
    payload: DatasetCreate,
    commands: Annotated[DatasetCommands, Depends(get_dataset_commands)],
) -> DatasetResponse:
    dataset = commands.create(payload.to_domain())
    return DatasetResponse.from_domain(dataset)


@router.post("/{dataset_name}/versions", response_model=DatasetVersionResponse)
def create_dataset_version(
    dataset_name: str,
    payload: DatasetVersionCreate,
    commands: Annotated[DatasetCommands, Depends(get_dataset_commands)],
) -> DatasetVersionResponse:
    try:
        version = commands.create_version(dataset_name, payload.to_domain())
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return DatasetVersionResponse.from_domain(version)
