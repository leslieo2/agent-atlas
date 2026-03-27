from __future__ import annotations

from app.bootstrap.bundles import (
    EvalModuleBundle,
    InfrastructureBundle,
    RunModuleBundle,
    WorkerBundle,
)
from app.bootstrap.worker import AppWorker


def build_worker_bundle(
    infra: InfrastructureBundle,
    runs: RunModuleBundle,
    evals: EvalModuleBundle,
) -> WorkerBundle:
    return WorkerBundle(
        app_worker=AppWorker(
            task_queue=infra.task_queue,
            run_execution_service=runs.run_execution_service,
            eval_execution_service=evals.eval_execution_service,
            eval_aggregation_service=evals.eval_aggregation_service,
        )
    )
