from __future__ import annotations

import json
import os
import shutil
import subprocess  # nosec B404
from pathlib import Path
from tempfile import TemporaryDirectory

from app.core.config import RunnerMode, settings
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
    _default_image = "agent-flight-recorder-backend:latest"

    def __init__(self, image: str | None = None) -> None:
        self.image = image or settings.runner_image or self._default_image

    def is_available(self) -> bool:
        return shutil.which("docker") is not None

    def execute(self, agent_type: AdapterKind, model: str, prompt: str) -> RuntimeExecutionResult:
        if not self.is_available():
            raise RuntimeError("docker binary not found")
        with TemporaryDirectory(prefix="aflight-docker-run-") as temp_dir:
            io_dir = Path(temp_dir)
            request_path = io_dir / "request.json"
            result_path = io_dir / "result.json"
            request_path.write_text(
                json.dumps(
                    {
                        "agent_type": agent_type.value,
                        "model": model,
                        "prompt": prompt,
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            completed = subprocess.run(  # nosec B603
                self._build_command(io_dir),
                capture_output=True,
                text=True,
                check=False,
            )
            if completed.returncode != 0:
                error_output = (
                    completed.stderr.strip() or completed.stdout.strip() or "unknown error"
                )
                raise RuntimeError(
                    "docker run failed with exit code " f"{completed.returncode}: {error_output}"
                )
            if not result_path.exists():
                raise RuntimeError("docker run completed without producing a result payload")
            payload = json.loads(result_path.read_text(encoding="utf-8"))

        result = RuntimeExecutionResult.model_validate(payload)
        return result.model_copy(
            update={"execution_backend": "docker", "container_image": self.image}
        )

    def _build_command(self, io_dir: Path) -> list[str]:
        command = [
            "docker",
            "run",
            "--rm",
            "-v",
            f"{io_dir}:/workspace/io",
            "-w",
            "/app",
            "-e",
            "AFLIGHT_RUN_REQUEST_PATH=/workspace/io/request.json",
            "-e",
            "AFLIGHT_RUN_RESULT_PATH=/workspace/io/result.json",
            "-e",
            "AFLIGHT_RUNTIME_MODE=live",
        ]
        command.extend(self._forwarded_env_args())
        command.extend(
            [
                self.image,
                "python",
                "-m",
                "app.infrastructure.adapters.docker_runtime",
            ]
        )
        return command

    @staticmethod
    def _forwarded_env_args() -> list[str]:
        args: list[str] = []
        for env_name in ("OPENAI_API_KEY", "AFLIGHT_OPENAI_API_KEY"):
            value = os.getenv(env_name)
            if value:
                args.extend(["-e", f"{env_name}={value}"])
        return args


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
    mode = settings.runner_mode
    if mode == RunnerMode.MOCK:
        return [_runners["mock"]]
    if mode == RunnerMode.LOCAL:
        return [_runners["local"]]
    if mode == RunnerMode.DOCKER:
        return [_runners["docker"]]

    if not settings.should_allow_mock_fallback(model_runtime_service.api_key):
        ordered: list[Runner] = [_runners["local"]]
        if _runners["docker"].is_available():
            ordered.insert(0, _runners["docker"])
        return ordered

    ordered = [_runners["local"], _runners["mock"]]
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
