from __future__ import annotations

import shutil
import threading
import traceback
from collections.abc import Callable
from dataclasses import dataclass
from queue import Queue

from app.core.config import settings
from app.infrastructure.adapters.model_runtime import model_runtime_service
from app.modules.runs.domain.models import RuntimeExecutionResult
from app.modules.shared.application.ports import TaskFn
from app.modules.shared.domain.enums import AdapterKind


class Runner:
    name = "base"

    def is_available(self) -> bool:
        return True

    def execute(self, agent_type: AdapterKind, model: str, prompt: str) -> RuntimeExecutionResult:
        raise NotImplementedError


class LocalRunner(Runner):
    name = "local"

    def execute(self, agent_type: AdapterKind, model: str, prompt: str) -> RuntimeExecutionResult:
        result = model_runtime_service.execute(agent_type, model, prompt)
        return result.model_copy(update={"execution_backend": "local", "container_image": None})


class DockerRunner(Runner):
    name = "docker"
    _default_image = "python:3.12-slim"

    def is_available(self) -> bool:
        return shutil.which("docker") is not None

    def execute(self, agent_type: AdapterKind, model: str, prompt: str) -> RuntimeExecutionResult:
        if not self.is_available():
            raise RuntimeError("docker binary not found")
        result = model_runtime_service.execute(agent_type, model, prompt)
        return result.model_copy(
            update={"execution_backend": "docker", "container_image": self._default_image}
        )


class MockRunner(Runner):
    name = "mock"

    def execute(self, agent_type: AdapterKind, model: str, prompt: str) -> RuntimeExecutionResult:
        result = model_runtime_service._simulate_output(agent_type, model, prompt)
        return result.model_copy(update={"execution_backend": "mock", "container_image": None})


_runners = {
    "local": LocalRunner(),
    "docker": DockerRunner(),
    "mock": MockRunner(),
}


def _ordered_runners() -> list[Runner]:
    mode = (settings.runner_mode or settings.runtime_mode or "auto").lower()
    if mode == "mock":
        return [_runners["mock"]]
    if mode == "local":
        return [_runners["local"]]
    if mode == "docker":
        if _runners["docker"].is_available():
            return [_runners["docker"], _runners["local"], _runners["mock"]]
        return [_runners["local"], _runners["mock"]]

    ordered: list[Runner] = [_runners["local"], _runners["mock"]]
    if _runners["docker"].is_available():
        ordered.insert(0, _runners["docker"])
    return ordered


def execute_with_fallback(
    agent_type: AdapterKind,
    model: str,
    prompt: str,
) -> RuntimeExecutionResult:
    last_error: Exception | None = None
    for runner in _ordered_runners():
        try:
            return runner.execute(agent_type, model, prompt)
        except Exception as exc:  # pragma: no cover
            last_error = exc
            continue
    raise RuntimeError(f"all runners failed; last_error={last_error}")


@dataclass
class _ScheduledTask:
    run_id: object
    fn: Callable[[], None]


class RunScheduler:
    def __init__(self, workers: int = 2) -> None:
        self._queue: Queue[_ScheduledTask] = Queue()
        self._workers = max(1, workers)
        self._started = False

    def start(self) -> None:
        if self._started:
            return
        for worker_id in range(self._workers):
            thread = threading.Thread(
                target=self._worker_loop,
                name=f"afr-run-scheduler-{worker_id+1}",
                daemon=True,
            )
            thread.start()
        self._started = True

    def submit(self, run_id: object, fn: TaskFn) -> None:
        if not self._started:
            self.start()
        self._queue.put(_ScheduledTask(run_id=run_id, fn=fn))

    def _worker_loop(self) -> None:
        while True:
            task = self._queue.get()
            try:
                task.fn()
            except Exception:
                traceback.print_exc()
            finally:
                self._queue.task_done()

    def pending_count(self) -> int:
        return self._queue.qsize()


run_scheduler = RunScheduler()


class FallbackRunnerAdapter:
    def execute(self, agent_type: AdapterKind, model: str, prompt: str) -> RuntimeExecutionResult:
        result = execute_with_fallback(agent_type, model, prompt)
        return RuntimeExecutionResult.model_validate(result)


class StaticRunnerRegistry:
    def __init__(self, default_runner: FallbackRunnerAdapter) -> None:
        self.default_runner = default_runner

    def get_runner(self, agent_type: AdapterKind) -> FallbackRunnerAdapter:
        return self.default_runner


class ThreadedSchedulerAdapter:
    def submit(self, run_id, fn: TaskFn) -> None:
        run_scheduler.submit(run_id, fn)
