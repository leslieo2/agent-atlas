from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.modules.datasets.domain.models import Dataset, DatasetVersion


class DatasetRepository(Protocol):
    def list(self) -> list[Dataset]: ...

    def get(self, name: str) -> Dataset | None: ...

    def get_version(self, dataset_version_id: UUID | str) -> DatasetVersion | None: ...

    def save(self, dataset: Dataset) -> None: ...
