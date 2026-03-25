from __future__ import annotations

from pydantic import BaseModel, Field


class DatasetSample(BaseModel):
    sample_id: str
    input: str
    expected: str | None = None
    tags: list[str] = Field(default_factory=list)


class Dataset(BaseModel):
    name: str
    rows: list[DatasetSample]


class DatasetCreate(BaseModel):
    name: str
    rows: list[DatasetSample]
