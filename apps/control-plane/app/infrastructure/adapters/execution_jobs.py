from __future__ import annotations

import asyncio
import concurrent.futures
import inspect
from collections.abc import Awaitable, Callable
from uuid import UUID

from arq.connections import ArqRedis, RedisSettings, create_pool

from app.modules.shared.application.ports import ExecutionJobPort, RunExecutionPayload
from app.modules.shared.domain.jobs import EnqueuedExecutionJob, ExecutionJobKind


def _run_execution_job_id(job_id: str) -> str:
    return f"run-execution:{job_id}"


def _experiment_execution_job_id(experiment_id: UUID) -> str:
    return f"experiment-execution:{experiment_id}"


def _experiment_aggregation_job_id(experiment_id: UUID) -> str:
    return f"experiment-aggregation:{experiment_id}"


class ArqExecutionJobQueue(ExecutionJobPort):
    def __init__(
        self,
        *,
        redis_settings: RedisSettings,
        queue_name: str,
        pool_factory: Callable[..., Awaitable[ArqRedis]] = create_pool,
    ) -> None:
        self.redis_settings = redis_settings
        self.queue_name = queue_name
        self.pool_factory = pool_factory

    def enqueue_run_execution(self, run_spec: RunExecutionPayload, *, job_id: str) -> None:
        self._enqueue(
            EnqueuedExecutionJob(
                job_id=_run_execution_job_id(job_id),
                kind=ExecutionJobKind.RUN_EXECUTION,
                kwargs={"run_spec": run_spec.model_dump(mode="json")},
            )
        )

    def enqueue_experiment_execution(self, experiment_id: UUID) -> None:
        self._enqueue(
            EnqueuedExecutionJob(
                job_id=_experiment_execution_job_id(experiment_id),
                kind=ExecutionJobKind.EXPERIMENT_EXECUTION,
                kwargs={"experiment_id": str(experiment_id)},
            )
        )

    def enqueue_experiment_aggregation(self, experiment_id: UUID) -> None:
        self._enqueue(
            EnqueuedExecutionJob(
                job_id=_experiment_aggregation_job_id(experiment_id),
                kind=ExecutionJobKind.EXPERIMENT_AGGREGATION,
                kwargs={"experiment_id": str(experiment_id)},
            )
        )

    def _enqueue(self, job: EnqueuedExecutionJob) -> None:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            asyncio.run(self._enqueue_async(job))
            return

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            executor.submit(lambda: asyncio.run(self._enqueue_async(job))).result()

    async def _enqueue_async(self, job: EnqueuedExecutionJob) -> None:
        redis = await self.pool_factory(
            self.redis_settings,
            default_queue_name=self.queue_name,
        )
        try:
            await redis.enqueue_job(
                job.kind.value,
                _job_id=job.job_id,
                _queue_name=self.queue_name,
                **job.kwargs,
            )
        finally:
            await _close_async_client(redis)


class InlineExecutionJobQueue(ExecutionJobPort):
    def __init__(self) -> None:
        self.enqueued: list[EnqueuedExecutionJob] = []

    def enqueue_run_execution(self, run_spec: RunExecutionPayload, *, job_id: str) -> None:
        self._append(
            EnqueuedExecutionJob(
                job_id=_run_execution_job_id(job_id),
                kind=ExecutionJobKind.RUN_EXECUTION,
                kwargs={"run_spec": run_spec.model_dump(mode="json")},
            )
        )

    def enqueue_experiment_execution(self, experiment_id: UUID) -> None:
        self._append(
            EnqueuedExecutionJob(
                job_id=_experiment_execution_job_id(experiment_id),
                kind=ExecutionJobKind.EXPERIMENT_EXECUTION,
                kwargs={"experiment_id": str(experiment_id)},
            )
        )

    def enqueue_experiment_aggregation(self, experiment_id: UUID) -> None:
        self._append(
            EnqueuedExecutionJob(
                job_id=_experiment_aggregation_job_id(experiment_id),
                kind=ExecutionJobKind.EXPERIMENT_AGGREGATION,
                kwargs={"experiment_id": str(experiment_id)},
            )
        )

    def _append(self, job: EnqueuedExecutionJob) -> None:
        if any(existing.job_id == job.job_id for existing in self.enqueued):
            return
        self.enqueued.append(job)

    def drain(self, *, handlers, limit: int = 10) -> int:
        processed = 0
        while self.enqueued and processed < limit:
            job = self.enqueued.pop(0)
            handlers.dispatch(job)
            processed += 1
        return processed


async def _close_async_client(client: ArqRedis) -> None:
    close = getattr(client, "aclose", None) or getattr(client, "close", None)
    if close is None:
        return
    try:
        result = close(close_connection_pool=True)
    except TypeError:
        result = close()
    if inspect.isawaitable(result):
        await result
