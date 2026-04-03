from __future__ import annotations

from typing import ClassVar, cast

from arq.connections import RedisSettings
from arq.typing import WorkerSettingsType
from arq.worker import run_worker

from app.bootstrap.container import get_container
from app.core.config import settings
from app.modules.shared.domain.jobs import EnqueuedExecutionJob, ExecutionJobKind


async def run_execution_job(run_spec: dict[str, object]) -> None:
    get_container().jobs.handlers.dispatch(
        EnqueuedExecutionJob(
            job_id="worker",
            kind=ExecutionJobKind.RUN_EXECUTION,
            kwargs={"run_spec": run_spec},
        )
    )


async def execute_experiment_job(experiment_id: str) -> None:
    get_container().jobs.handlers.dispatch(
        EnqueuedExecutionJob(
            job_id="worker",
            kind=ExecutionJobKind.EXPERIMENT_EXECUTION,
            kwargs={"experiment_id": experiment_id},
        )
    )


async def refresh_experiment_job(experiment_id: str) -> None:
    get_container().jobs.handlers.dispatch(
        EnqueuedExecutionJob(
            job_id="worker",
            kind=ExecutionJobKind.EXPERIMENT_AGGREGATION,
            kwargs={"experiment_id": experiment_id},
        )
    )


class WorkerSettings:
    functions: ClassVar[list] = [run_execution_job, execute_experiment_job, refresh_experiment_job]
    redis_settings: ClassVar[RedisSettings] = RedisSettings.from_dsn(
        settings.execution_job_queue_url
    )
    queue_name: ClassVar[str] = settings.execution_job_queue_name
    max_tries: ClassVar[int] = 1
    keep_result: ClassVar[int] = 0


def main() -> None:
    run_worker(cast(WorkerSettingsType, WorkerSettings))


if __name__ == "__main__":
    main()
