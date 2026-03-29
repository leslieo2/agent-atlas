from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

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


class Dataset(BaseModel):
    name: str
    description: str | None = None
    source: str | None = None
    version: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    rows: list[DatasetSample]


class DatasetCreate(BaseModel):
    name: str
    description: str | None = None
    source: str | None = None
    version: str | None = None
    rows: list[DatasetSample]
