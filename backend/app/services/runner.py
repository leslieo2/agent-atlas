from __future__ import annotations

import shutil
from typing import Any

from app.core.config import settings
from app.models.schemas import AdapterKind
from app.services.model_runtime import model_runtime_service


class Runner:
    name = "base"

    def execute(self, agent_type: AdapterKind, model: str, prompt: str) -> dict[str, Any]:
        raise NotImplementedError


class LocalRunner(Runner):
    name = "local"

    def execute(self, agent_type: AdapterKind, model: str, prompt: str) -> dict[str, Any]:
        result = model_runtime_service.execute(agent_type, model, prompt)
        return {
            **result,
            "execution_backend": "local",
            "container_image": None,
        }


class DockerRunner(Runner):
    name = "docker"
    _default_image = "python:3.12-slim"

    def is_available(self) -> bool:
        return shutil.which("docker") is not None

    def execute(self, agent_type: AdapterKind, model: str, prompt: str) -> dict[str, Any]:
        if not self.is_available():
            raise RuntimeError("docker binary not found")
        result = model_runtime_service.execute(agent_type, model, prompt)
        return {
            **result,
            "execution_backend": "docker",
            "container_image": self._default_image,
        }


class MockRunner(Runner):
    name = "mock"

    def execute(self, agent_type: AdapterKind, model: str, prompt: str) -> dict[str, Any]:
        result = model_runtime_service._simulate_output(agent_type, model, prompt)
        return {
            **result,
            "execution_backend": "mock",
            "container_image": None,
        }


_runners = {
    "local": LocalRunner(),
    "docker": DockerRunner(),
    "mock": MockRunner(),
}


def _choose_runner() -> Runner:
    mode = (settings.runner_mode or settings.runtime_mode or "auto").lower()
    if mode == "local":
        return _runners["local"]
    if mode == "docker":
        if _runners["docker"].is_available():
            return _runners["docker"]
        return _runners["local"]
    if mode == "mock":
        return _runners["mock"]

    if _runners["docker"].is_available():
        return _runners["docker"]
    return _runners["local"]


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

    # auto: prefer docker isolation, then local, then mock fallback
    ordered: list[Runner] = [_runners["local"], _runners["mock"]]
    if _runners["docker"].is_available():
        ordered.insert(0, _runners["docker"])
    return ordered


def execute_with_fallback(agent_type: AdapterKind, model: str, prompt: str) -> dict[str, Any]:
    last_error: Exception | None = None
    for runner in _ordered_runners():
        try:
            return runner.execute(agent_type, model, prompt)
        except Exception as exc:  # pragma: no cover
            last_error = exc
            continue
    raise RuntimeError(f"all runners failed; last_error={last_error}")


execution_runner = _choose_runner()
