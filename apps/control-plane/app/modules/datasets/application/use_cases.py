from __future__ import annotations

from app.modules.datasets.application.ports import DatasetRepository
from app.modules.datasets.domain.models import (
    Dataset,
    DatasetCreate,
    DatasetVersion,
    DatasetVersionCreate,
)


class DatasetQueries:
    def __init__(self, dataset_repository: DatasetRepository) -> None:
        self.dataset_repository = dataset_repository

    def list(self) -> list[Dataset]:
        return self.dataset_repository.list()

    def get(self, name: str) -> Dataset | None:
        return self.dataset_repository.get(name)

    def get_version(self, dataset_version_id: str) -> DatasetVersion | None:
        return self.dataset_repository.get_version(dataset_version_id)


class DatasetCommands:
    def __init__(self, dataset_repository: DatasetRepository) -> None:
        self.dataset_repository = dataset_repository

    def create(self, payload: DatasetCreate) -> Dataset:
        version = DatasetVersion(
            dataset_name=payload.name,
            version=payload.version,
            rows=payload.rows,
        )
        dataset = Dataset(
            name=payload.name,
            description=payload.description,
            source=payload.source,
            current_version_id=version.dataset_version_id,
            versions=[version],
        )
        self.dataset_repository.save(dataset)
        return dataset

    def create_version(self, dataset_name: str, payload: DatasetVersionCreate) -> DatasetVersion:
        dataset = self.dataset_repository.get(dataset_name)
        if dataset is None:
            raise ValueError(f"dataset '{dataset_name}' was not found")
        version = DatasetVersion(
            dataset_name=dataset_name,
            version=payload.version,
            rows=payload.rows,
        )
        dataset = dataset.model_copy(
            update={
                "current_version_id": version.dataset_version_id,
                "versions": [*dataset.versions, version],
            }
        )
        self.dataset_repository.save(dataset)
        return version
