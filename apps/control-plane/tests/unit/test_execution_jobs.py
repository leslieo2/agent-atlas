from __future__ import annotations

import asyncio
from uuid import uuid4

from app import worker
from app.infrastructure.adapters.execution_jobs import ArqExecutionJobQueue
from app.modules.runs.domain.models import RunExecutionSpec as ExecutionRunSpec
from app.modules.shared.domain.enums import AdapterKind
from app.modules.shared.domain.jobs import ExecutionJobKind
from arq.connections import RedisSettings


class FakeArqRedis:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str, dict[str, object]]] = []
        self.closed = False

    async def enqueue_job(self, function: str, *, _job_id: str, _queue_name: str, **kwargs) -> None:
        self.calls.append((function, _job_id, _queue_name, kwargs))

    async def aclose(self, *, close_connection_pool: bool = False) -> None:
        assert close_connection_pool is True
        self.closed = True


def test_arq_execution_job_queue_enqueues_run_execution_with_stable_job_id() -> None:
    fake_redis = FakeArqRedis()

    async def pool_factory(*args, **kwargs):
        del args, kwargs
        return fake_redis

    queue = ArqExecutionJobQueue(
        redis_settings=RedisSettings(),
        queue_name="atlas-test-jobs",
        pool_factory=pool_factory,
    )
    run_spec = ExecutionRunSpec(
        run_id=uuid4(),
        project="control-plane",
        dataset="dataset-v1",
        agent_id="basic",
        model="gpt-5.4-mini",
        entrypoint="tests.fixtures.agents.basic:build_agent",
        agent_type=AdapterKind.OPENAI_AGENTS,
        input_summary="run input",
        prompt="Summarize this run.",
    )

    queue.enqueue_run_execution(run_spec, job_id="local-123")

    assert fake_redis.calls == [
        (
            "run_execution_job",
            "run-execution:local-123",
            "atlas-test-jobs",
            {"run_spec": run_spec.model_dump(mode="json")},
        )
    ]
    assert fake_redis.closed is True


def test_run_execution_worker_accepts_arq_ctx_and_keyword_payload(monkeypatch) -> None:
    dispatched = []

    class FakeHandlers:
        def dispatch(self, job) -> None:
            dispatched.append(job)

    class FakeJobs:
        handlers = FakeHandlers()

    class FakeContainer:
        jobs = FakeJobs()

    monkeypatch.setattr(worker, "get_container", lambda: FakeContainer())

    payload = {"run_id": str(uuid4()), "project": "atlas-validation"}

    asyncio.run(worker.run_execution_job({}, run_spec=payload))

    assert len(dispatched) == 1
    assert dispatched[0].kind == ExecutionJobKind.RUN_EXECUTION
    assert dispatched[0].kwargs == {"run_spec": payload}


def test_experiment_workers_accept_arq_ctx_and_keyword_payload(monkeypatch) -> None:
    dispatched = []

    class FakeHandlers:
        def dispatch(self, job) -> None:
            dispatched.append(job)

    class FakeJobs:
        handlers = FakeHandlers()

    class FakeContainer:
        jobs = FakeJobs()

    monkeypatch.setattr(worker, "get_container", lambda: FakeContainer())

    asyncio.run(worker.execute_experiment_job({}, experiment_id="exp-123"))
    asyncio.run(worker.refresh_experiment_job({}, experiment_id="exp-456"))

    assert [job.kind for job in dispatched] == [
        ExecutionJobKind.EXPERIMENT_EXECUTION,
        ExecutionJobKind.EXPERIMENT_AGGREGATION,
    ]
    assert [job.kwargs for job in dispatched] == [
        {"experiment_id": "exp-123"},
        {"experiment_id": "exp-456"},
    ]
