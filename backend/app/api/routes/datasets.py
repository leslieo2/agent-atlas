from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.bootstrap.providers.datasets import get_dataset_commands, get_dataset_queries
from app.modules.datasets.api.schemas import DatasetCreate, DatasetResponse
from app.modules.datasets.application.use_cases import DatasetCommands, DatasetQueries

router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.get("", response_model=list[DatasetResponse])
def list_datasets(
    queries: Annotated[DatasetQueries, Depends(get_dataset_queries)],
) -> list[DatasetResponse]:
    return [DatasetResponse.from_domain(dataset) for dataset in queries.list()]


@router.post("", response_model=DatasetResponse)
def create_dataset(
    payload: DatasetCreate,
    commands: Annotated[DatasetCommands, Depends(get_dataset_commands)],
) -> DatasetResponse:
    dataset = commands.create(payload.to_domain())
    return DatasetResponse.from_domain(dataset)
