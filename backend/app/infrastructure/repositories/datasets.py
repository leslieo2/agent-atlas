from __future__ import annotations

from app.infrastructure.repositories.common import persistence
from app.modules.datasets.domain.models import Dataset


class StateDatasetRepository:
    def list(self) -> list[Dataset]:
        return persistence.list_datasets()

    def get(self, name: str) -> Dataset | None:
        return persistence.get_dataset(name)

    def save(self, dataset: Dataset) -> None:
        persistence.save_dataset(dataset)

__all__ = ["StateDatasetRepository"]
