from __future__ import annotations

from app.db.state import state
from app.models.schemas import Dataset, DatasetCreate


class DatasetService:
    def list(self) -> list[Dataset]:
        with state.lock:
            return list(state.datasets.values())

    def create(self, payload: DatasetCreate) -> Dataset:
        dataset = Dataset(name=payload.name, rows=payload.rows)
        with state.lock:
            state.datasets[dataset.name] = dataset
            state.save_dataset(dataset)
        return dataset

    def get(self, name: str) -> Dataset | None:
        with state.lock:
            return state.datasets.get(name)


dataset_service = DatasetService()
