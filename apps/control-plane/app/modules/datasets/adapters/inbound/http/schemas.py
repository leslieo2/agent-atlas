from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.modules.datasets.domain.models import Dataset, DatasetSample, DatasetVersion
from app.modules.datasets.domain.models import DatasetCreate as DomainDatasetCreate
from app.modules.datasets.domain.models import DatasetVersionCreate as DomainDatasetVersionCreate


class DatasetCreate(BaseModel):
    name: str
    description: str | None = None
    source: str | None = None
    version: str | None = None
    rows: list[DatasetSample]

    def to_domain(self) -> DomainDatasetCreate:
        return DomainDatasetCreate.model_validate(self.model_dump())


class DatasetVersionCreate(BaseModel):
    version: str | None = None
    rows: list[DatasetSample]

    def to_domain(self) -> DomainDatasetVersionCreate:
        return DomainDatasetVersionCreate.model_validate(self.model_dump())


class DatasetVersionResponse(BaseModel):
    dataset_version_id: UUID
    dataset_name: str
    version: str | None = None
    created_at: datetime
    row_count: int
    rows: list[DatasetSample]

    @classmethod
    def from_domain(cls, version: DatasetVersion) -> DatasetVersionResponse:
        return cls(
            dataset_version_id=version.dataset_version_id,
            dataset_name=version.dataset_name,
            version=version.version,
            created_at=version.created_at,
            row_count=len(version.rows),
            rows=version.rows,
        )


class DatasetResponse(BaseModel):
    name: str
    description: str | None = None
    source: str | None = None
    created_at: datetime
    version: str | None = None
    row_count: int = 0
    rows: list[DatasetSample] = Field(default_factory=list)
    current_version_id: UUID | None = None
    versions: list[DatasetVersionResponse]

    @classmethod
    def from_domain(cls, dataset: Dataset) -> DatasetResponse:
        current_version = dataset.current_version()
        return cls(
            name=dataset.name,
            description=dataset.description,
            source=dataset.source,
            created_at=dataset.created_at,
            version=current_version.version if current_version else None,
            row_count=len(current_version.rows) if current_version else 0,
            rows=list(current_version.rows) if current_version else [],
            current_version_id=dataset.current_version_id,
            versions=[DatasetVersionResponse.from_domain(version) for version in dataset.versions],
        )
