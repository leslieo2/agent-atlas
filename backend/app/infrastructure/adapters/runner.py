from __future__ import annotations

import shutil

from app.core.config import settings
from app.infrastructure.adapters.model_runtime import model_runtime_service
from app.modules.runs.domain.models import RuntimeExecutionResult
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


class FallbackRunnerAdapter:
    def execute(self, agent_type: AdapterKind, model: str, prompt: str) -> RuntimeExecutionResult:
        result = execute_with_fallback(agent_type, model, prompt)
        return RuntimeExecutionResult.model_validate(result)


class StaticRunnerRegistry:
    def __init__(self, default_runner: FallbackRunnerAdapter) -> None:
        self.default_runner = default_runner

    def get_runner(self, agent_type: AdapterKind) -> FallbackRunnerAdapter:
        return self.default_runner
