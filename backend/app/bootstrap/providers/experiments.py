from __future__ import annotations

from app.bootstrap.container import get_container
from app.modules.experiments.application.use_cases import ExperimentCommands, ExperimentQueries


def get_experiment_queries() -> ExperimentQueries:
    return get_container().experiments.experiment_queries


def get_experiment_commands() -> ExperimentCommands:
    return get_container().experiments.experiment_commands
