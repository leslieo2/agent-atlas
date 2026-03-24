from __future__ import annotations

from fastapi import APIRouter

from app.models.schemas import Dataset, DatasetCreate
from app.services.datasets import dataset_service

router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.get("", response_model=list[Dataset])
def list_datasets() -> list[Dataset]:
    return dataset_service.list()


@router.post("", response_model=Dataset)
def create_dataset(payload: DatasetCreate) -> Dataset:
    return dataset_service.create(payload)
