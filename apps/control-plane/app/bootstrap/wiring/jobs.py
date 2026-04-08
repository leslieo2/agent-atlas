from __future__ import annotations

from dataclasses import dataclass

from app.bootstrap.jobs import ExecutionJobHandlers
from app.bootstrap.wiring.experiments import ExperimentModuleBundle
from app.bootstrap.wiring.runs import RunModuleBundle


@dataclass(frozen=True)
class JobBundle:
    handlers: ExecutionJobHandlers


def build_job_bundle(runs: RunModuleBundle, experiments: ExperimentModuleBundle) -> JobBundle:
    return JobBundle(
        handlers=ExecutionJobHandlers(
            run_execution_service=runs.run_execution_service,
            experiment_execution_service=experiments.experiment_execution_service,
            experiment_aggregation_service=experiments.experiment_aggregation_service,
        )
    )
