from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.modules.datasets.domain.models import Dataset, DatasetSample
from app.modules.datasets.domain.models import DatasetCreate as DomainDatasetCreate


class DatasetCreate(BaseModel):
    name: str
    description: str | None = None
    source: str | None = None
    version: str | None = None
    rows: list[DatasetSample]

    def to_domain(self) -> DomainDatasetCreate:
        return DomainDatasetCreate.model_validate(self.model_dump())


class DatasetResponse(BaseModel):
    name: str
    description: str | None = None
    source: str | None = None
    version: str | None = None
    created_at: datetime
    rows: list[DatasetSample]

    @classmethod
    def from_domain(cls, dataset: Dataset) -> DatasetResponse:
        return cls.model_validate(dataset.model_dump(mode="json"))
