from __future__ import annotations

from typing import Protocol

from app.modules.datasets.domain.models import Dataset


class DatasetRepository(Protocol):
    def list(self) -> list[Dataset]: ...

    def get(self, name: str) -> Dataset | None: ...

    def save(self, dataset: Dataset) -> None: ...
