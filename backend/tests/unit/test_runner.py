from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from app.core.config import RunnerMode, RuntimeMode
from app.infrastructure.adapters import runner
from app.infrastructure.adapters.model_runtime import ModelRuntimeService
from app.modules.shared.domain.enums import AdapterKind
from pydantic import SecretStr


def test_runner_prefers_docker_when_available_in_auto_mode(monkeypatch):
    runtime_service = ModelRuntimeService()
    monkeypatch.setattr(runner.settings, "runner_mode", RunnerMode.AUTO)
    monkeypatch.setattr(runner.settings, "runtime_mode", RuntimeMode.AUTO)
    monkeypatch.setattr(runner.settings, "openai_api_key", None)
    monkeypatch.setattr(runtime_service, "api_key", None)
    monkeypatch.setattr(runner.DockerRunner, "is_available", lambda self: True)

    ordered = runner._ordered_runners(runtime_service)

    assert ordered[0].name == "docker"
    assert ordered[1].name == "local"
    assert ordered[2].name == "mock"


def test_runner_falls_back_to_mock_when_mode_is_mock(monkeypatch):
    runtime_service = ModelRuntimeService()
    monkeypatch.setattr(runner.settings, "runner_mode", RunnerMode.MOCK)

    ordered = runner._ordered_runners(runtime_service)

    assert len(ordered) == 1
    assert ordered[0].name == "mock"


def test_runner_docker_mode_does_not_include_local_or_mock_fallbacks(monkeypatch):
    runtime_service = ModelRuntimeService()
    monkeypatch.setattr(runner.settings, "runner_mode", RunnerMode.DOCKER)
    monkeypatch.setattr(runner.DockerRunner, "is_available", lambda self: True)

    ordered = runner._ordered_runners(runtime_service)

    assert [item.name for item in ordered] == ["docker"]


def test_runner_auto_mode_does_not_fallback_to_mock_in_live_runtime(monkeypatch):
    runtime_service = ModelRuntimeService()
    monkeypatch.setattr(runner.settings, "runner_mode", RunnerMode.AUTO)
    monkeypatch.setattr(runner.settings, "runtime_mode", RuntimeMode.LIVE)
    monkeypatch.setattr(runtime_service, "api_key", SecretStr("sk-test"))
    monkeypatch.setattr(runner.DockerRunner, "is_available", lambda self: False)

    ordered = runner._ordered_runners(runtime_service)

    assert [item.name for item in ordered] == ["local"]


def test_static_runner_registry_returns_default_runner():
    default_runner = runner.FallbackRunnerAdapter(runtime_service=ModelRuntimeService())
    registry = runner.StaticRunnerRegistry(default_runner=default_runner)

    selected = registry.get_runner("openai-agents-sdk")

    assert selected is default_runner


def test_docker_runner_executes_inside_container_and_reads_result(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(runner.settings, "runner_image", "agent-atlas-backend:test")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    calls: list[list[str]] = []

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        assert kwargs["capture_output"] is True
        assert kwargs["text"] is True
        assert kwargs["check"] is False
        assert command[:3] == ["docker", "run", "--rm"]
        assert "agent-atlas-backend:test" in command
        assert command[-3:] == ["python", "-m", "app.infrastructure.adapters.docker_runtime"]
        assert "OPENAI_API_KEY=sk-test" in command
        assert "AGENT_ATLAS_RUNTIME_MODE=live" in command

        io_dir = _mounted_host_dir(command, "/workspace/io")
        assert "-w" in command
        assert command[command.index("-w") + 1] == "/app"
        assert all("/workspace/backend" not in token for token in command)

        request = json.loads((io_dir / "request.json").read_text(encoding="utf-8"))
        assert request == {
            "agent_type": "openai-agents-sdk",
            "model": "gpt-5.4-mini",
            "prompt": "Summarize the ticket.",
        }

        (io_dir / "result.json").write_text(
            json.dumps(
                {
                    "output": "isolated output",
                    "latency_ms": 42,
                    "token_usage": 17,
                    "provider": "docker-runtime",
                }
            ),
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(command, 0, stdout="done", stderr="")

    monkeypatch.setattr(runner.subprocess, "run", fake_run)

    docker_runner = runner.DockerRunner()
    result = docker_runner.execute(
        AdapterKind.OPENAI_AGENTS,
        model="gpt-5.4-mini",
        prompt="Summarize the ticket.",
    )

    assert len(calls) == 1
    assert result.output == "isolated output"
    assert result.provider == "docker-runtime"
    assert result.execution_backend == "docker"
    assert result.container_image == "agent-atlas-backend:test"


def test_docker_runner_raises_when_container_execution_fails(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(runner.settings, "runner_image", "agent-atlas-backend:test")

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 1, stdout="stdout trace", stderr="stderr trace")

    monkeypatch.setattr(runner.subprocess, "run", fake_run)

    docker_runner = runner.DockerRunner()

    with pytest.raises(RuntimeError, match="docker run failed"):
        docker_runner.execute(
            AdapterKind.OPENAI_AGENTS,
            model="gpt-5.4-mini",
            prompt="Summarize the ticket.",
        )


def _mounted_host_dir(command: list[str], container_path: str) -> Path:
    for index, token in enumerate(command):
        if token != "-v":
            continue
        host_path, mounted_path, *_rest = command[index + 1].split(":")
        if mounted_path == container_path:
            return Path(host_path)
    raise AssertionError(f"mount for {container_path} not found")
