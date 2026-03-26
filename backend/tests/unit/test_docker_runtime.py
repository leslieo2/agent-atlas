from __future__ import annotations

import json
from pathlib import Path

import pytest
from app.infrastructure.adapters import docker_runtime
from app.modules.runs.domain.models import RuntimeExecutionResult


def test_docker_runtime_reads_request_and_writes_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    request_path = tmp_path / "request.json"
    result_path = tmp_path / "result.json"
    request_path.write_text(
        json.dumps(
            {
                "agent_type": "openai-agents-sdk",
                "model": "gpt-4.1-mini",
                "prompt": "Summarize the ticket.",
            }
        ),
        encoding="utf-8",
    )

    def fake_execute(agent_type: object, model: str, prompt: str) -> RuntimeExecutionResult:
        assert str(agent_type) == "AdapterKind.OPENAI_AGENTS"
        assert model == "gpt-4.1-mini"
        assert prompt == "Summarize the ticket."
        return RuntimeExecutionResult(
            output="container output",
            latency_ms=11,
            token_usage=22,
            provider="mock",
        )

    class StubRuntimeService:
        execute = staticmethod(fake_execute)

    monkeypatch.setattr(
        docker_runtime,
        "build_runtime_service",
        lambda: StubRuntimeService(),
    )
    monkeypatch.setenv("AGENT_ATLAS_RUN_REQUEST_PATH", str(request_path))
    monkeypatch.setenv("AGENT_ATLAS_RUN_RESULT_PATH", str(result_path))

    docker_runtime.main()

    payload = json.loads(result_path.read_text(encoding="utf-8"))
    assert payload == {
        "output": "container output",
        "latency_ms": 11,
        "token_usage": 22,
        "provider": "mock",
        "execution_backend": None,
        "container_image": None,
        "resolved_model": None,
    }
