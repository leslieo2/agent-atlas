from __future__ import annotations

from uuid import UUID

from app.infrastructure.repositories.common import persistence, to_uuid
from app.modules.datasets.domain.models import Dataset, DatasetVersion


class StateDatasetRepository:
    def list(self) -> list[Dataset]:
        return persistence.list_datasets()

    def get(self, name: str) -> Dataset | None:
        return persistence.get_dataset(name)

    def get_version(self, dataset_version_id: UUID | str) -> DatasetVersion | None:
        return persistence.get_dataset_version(to_uuid(dataset_version_id))

    def save(self, dataset: Dataset) -> None:
        persistence.save_dataset(dataset)


__all__ = ["StateDatasetRepository"]
