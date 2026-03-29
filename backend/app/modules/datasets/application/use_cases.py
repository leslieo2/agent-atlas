from __future__ import annotations

from app.modules.datasets.application.ports import DatasetRepository
from app.modules.datasets.domain.models import Dataset, DatasetCreate


class DatasetQueries:
    def __init__(self, dataset_repository: DatasetRepository) -> None:
        self.dataset_repository = dataset_repository

    def list(self) -> list[Dataset]:
        return self.dataset_repository.list()

    def get(self, name: str) -> Dataset | None:
        return self.dataset_repository.get(name)


class DatasetCommands:
    def __init__(self, dataset_repository: DatasetRepository) -> None:
        self.dataset_repository = dataset_repository

    def create(self, payload: DatasetCreate) -> Dataset:
        dataset = Dataset(
            name=payload.name,
            description=payload.description,
            source=payload.source,
            version=payload.version,
            rows=payload.rows,
        )
        self.dataset_repository.save(dataset)
        return dataset
