from __future__ import annotations

from dataclasses import dataclass

from app.bootstrap.wiring.experiments import ExperimentModuleBundle
from app.bootstrap.wiring.infrastructure import InfrastructureBundle
from app.bootstrap.wiring.runs import RunModuleBundle
from app.bootstrap.worker import AppWorker


@dataclass(frozen=True)
class WorkerBundle:
    app_worker: AppWorker


def build_worker_bundle(
    infra: InfrastructureBundle,
    runs: RunModuleBundle,
    experiments: ExperimentModuleBundle,
) -> WorkerBundle:
    return WorkerBundle(
        app_worker=AppWorker(
            task_queue=infra.execution.task_queue,
            run_execution_service=runs.run_execution_service,
            experiment_orchestrator=experiments.experiment_orchestrator,
            experiment_aggregation_service=experiments.experiment_aggregation_service,
        )
    )
