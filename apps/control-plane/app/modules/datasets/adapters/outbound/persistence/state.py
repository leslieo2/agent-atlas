from __future__ import annotations

from uuid import UUID

from app.db.persistence import StatePersistence
from app.infrastructure.repositories.common import (
    StatePersistenceSource,
    resolve_state_persistence,
    to_uuid,
)
from app.modules.datasets.domain.models import Dataset, DatasetVersion


class StateDatasetRepository:
    def __init__(self, persistence: StatePersistenceSource = None) -> None:
        self._persistence_source = persistence

    @property
    def _persistence(self) -> StatePersistence:
        return resolve_state_persistence(self._persistence_source)

    def list(self) -> list[Dataset]:
        return self._persistence.list_datasets()

    def get(self, name: str) -> Dataset | None:
        return self._persistence.get_dataset(name)

    def get_version(self, dataset_version_id: UUID | str) -> DatasetVersion | None:
        return self._persistence.get_dataset_version(to_uuid(dataset_version_id))

    def save(self, dataset: Dataset) -> None:
        self._persistence.save_dataset(dataset)


__all__ = ["StateDatasetRepository"]
