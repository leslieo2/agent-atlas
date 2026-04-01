from __future__ import annotations

from typing import cast
from uuid import UUID

from app.db.persistence import StatePersistence
from app.infrastructure.repositories.common import persistence, to_uuid
from app.modules.datasets.domain.models import Dataset, DatasetVersion

state_persistence = cast(StatePersistence, persistence)


class StateDatasetRepository:
    def list(self) -> list[Dataset]:
        return state_persistence.list_datasets()

    def get(self, name: str) -> Dataset | None:
        return state_persistence.get_dataset(name)

    def get_version(self, dataset_version_id: UUID | str) -> DatasetVersion | None:
        return state_persistence.get_dataset_version(to_uuid(dataset_version_id))

    def save(self, dataset: Dataset) -> None:
        state_persistence.save_dataset(dataset)


__all__ = ["StateDatasetRepository"]
