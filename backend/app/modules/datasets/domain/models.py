from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(UTC)


class DatasetSample(BaseModel):
    sample_id: str
    input: str
    expected: str | None = None
    tags: list[str] = Field(default_factory=list)
    slice: str | None = None
    source: str | None = None
    metadata: dict[str, Any] | None = None
    export_eligible: bool | None = None


class DatasetVersion(BaseModel):
    dataset_version_id: UUID = Field(default_factory=uuid4)
    dataset_name: str
    version: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    rows: list[DatasetSample] = Field(default_factory=list)


class Dataset(BaseModel):
    name: str
    description: str | None = None
    source: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    current_version_id: UUID | None = None
    versions: list[DatasetVersion] = Field(default_factory=list)

    def current_version(self) -> DatasetVersion | None:
        if self.current_version_id is None:
            return self.versions[-1] if self.versions else None
        for version in self.versions:
            if version.dataset_version_id == self.current_version_id:
                return version
        return self.versions[-1] if self.versions else None


class DatasetCreate(BaseModel):
    name: str
    description: str | None = None
    source: str | None = None
    version: str | None = None
    rows: list[DatasetSample]


class DatasetVersionCreate(BaseModel):
    version: str | None = None
    rows: list[DatasetSample]
