from __future__ import annotations

from app.bootstrap.container import get_container
from app.modules.datasets.application.use_cases import DatasetCommands, DatasetQueries


def get_dataset_queries() -> DatasetQueries:
    return get_container().datasets.dataset_queries


def get_dataset_commands() -> DatasetCommands:
    return get_container().datasets.dataset_commands
