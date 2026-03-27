from __future__ import annotations

from dataclasses import dataclass

from app.bootstrap.wiring.infrastructure import InfrastructureBundle
from app.modules.datasets.application.use_cases import DatasetCommands, DatasetQueries


@dataclass(frozen=True)
class DatasetModuleBundle:
    dataset_queries: DatasetQueries
    dataset_commands: DatasetCommands


def build_dataset_module(infra: InfrastructureBundle) -> DatasetModuleBundle:
    dataset_queries = DatasetQueries(dataset_repository=infra.dataset_repository)
    dataset_commands = DatasetCommands(dataset_repository=infra.dataset_repository)

    return DatasetModuleBundle(
        dataset_queries=dataset_queries,
        dataset_commands=dataset_commands,
    )
