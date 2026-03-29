from __future__ import annotations

from typing import Protocol

from app.modules.datasets.domain.models import Dataset
from app.modules.evals.application.ports import DatasetSourcePort
from app.modules.evals.domain.models import EvalDataset, EvalDatasetSample


class _DatasetReader(Protocol):
    def get(self, name: str) -> Dataset | None: ...


class EvalDatasetSourceAdapter(DatasetSourcePort):
    def __init__(self, dataset_repository: _DatasetReader) -> None:
        self.dataset_repository = dataset_repository

    def get(self, name: str) -> EvalDataset | None:
        dataset = self.dataset_repository.get(name)
        if dataset is None:
            return None

        return EvalDataset(
            name=dataset.name,
            samples=[
                EvalDatasetSample(
                    sample_id=sample.sample_id,
                    input=sample.input,
                    expected=sample.expected,
                    tags=sample.tags,
                    slice=sample.slice,
                    source=sample.source,
                    metadata=sample.metadata,
                    export_eligible=sample.export_eligible,
                )
                for sample in dataset.rows
            ],
        )
