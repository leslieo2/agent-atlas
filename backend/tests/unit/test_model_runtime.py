from __future__ import annotations

import os
import sys
from types import ModuleType, SimpleNamespace

import pytest
from app.core.errors import (
    ModelNotFoundError,
    ProviderAuthError,
    ProviderTimeoutError,
    RateLimitedError,
    UnsupportedAdapterError,
)
from app.infrastructure.adapters.model_runtime import ModelRuntimeService
from app.modules.runs.domain.models import RuntimeExecutionResult
from app.modules.shared.domain.enums import AdapterKind
from pydantic import SecretStr


def test_model_runtime_service_uses_openai_agents_sdk_runner(monkeypatch: pytest.MonkeyPatch):
    calls: dict[str, object] = {}
    fake_agents = ModuleType("agents")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    class Agent:
        def __init__(self, *, name: str, instructions: str, model: str) -> None:
            calls["agent"] = {
                "name": name,
                "instructions": instructions,
                "model": model,
            }

    class Runner:
        @staticmethod
        def run_sync(agent: Agent, prompt: str) -> SimpleNamespace:
            calls["run_sync"] = {"agent": agent, "prompt": prompt}
            calls["api_key"] = os.environ.get("OPENAI_API_KEY")
            usage = SimpleNamespace(total_tokens=123)
            context_wrapper = SimpleNamespace(usage=usage)
            return SimpleNamespace(final_output="sdk output", context_wrapper=context_wrapper)

    fake_agents.Agent = Agent
    fake_agents.Runner = Runner
    monkeypatch.setitem(sys.modules, "agents", fake_agents)

    service = ModelRuntimeService()
    service.api_key = SecretStr("sk-test")
    service.runtime_mode = "live"

    result = service.execute(
        AdapterKind.OPENAI_AGENTS,
        model="gpt-4.1-mini",
        prompt="Summarize the ticket.",
    )

    assert calls["agent"] == {
        "name": "Agent Flight Recorder Assistant",
        "instructions": (
            "You are a concise assistant inside Agent Flight Recorder. "
            "Return the best direct answer."
        ),
        "model": "gpt-4.1-mini",
    }
    assert calls["api_key"] == "sk-test"
    assert calls["run_sync"]["prompt"] == "Summarize the ticket."
    assert result == RuntimeExecutionResult(
        output="sdk output",
        latency_ms=result.latency_ms,
        token_usage=123,
        provider="openai-agents-sdk",
    )
    assert result.latency_ms >= 0


def test_model_runtime_service_raises_clear_error_when_agents_sdk_missing():
    sys.modules.pop("agents", None)
    sys.modules["agents"] = None
    service = ModelRuntimeService()
    service.api_key = SecretStr("sk-test")
    service.runtime_mode = "live"

    try:
        with pytest.raises(
            RuntimeError,
            match="OpenAI Agents SDK package 'agents' is not installed",
        ):
            service.execute(
                AdapterKind.OPENAI_AGENTS,
                model="gpt-4.1-mini",
                prompt="Summarize the ticket.",
            )
    finally:
        sys.modules.pop("agents", None)


def test_model_runtime_service_dispatches_through_registered_adapters():
    class StubAdapter:
        def __init__(self) -> None:
            self.calls: list[tuple[str, str]] = []

        def execute(
            self,
            *,
            api_key: SecretStr | None,
            model: str,
            prompt: str,
        ) -> RuntimeExecutionResult:
            self.calls.append((model, prompt))
            assert api_key is not None
            return RuntimeExecutionResult(
                output=f"stub:{prompt}",
                latency_ms=7,
                token_usage=9,
                provider="stub",
            )

    adapter = StubAdapter()
    service = ModelRuntimeService(adapters={AdapterKind.LANGCHAIN: adapter})
    service.api_key = SecretStr("sk-test")
    service.runtime_mode = "live"

    result = service.execute(
        AdapterKind.LANGCHAIN,
        model="gpt-4.1-mini",
        prompt="Check the account state.",
    )

    assert adapter.calls == [("gpt-4.1-mini", "Check the account state.")]
    assert result.provider == "stub"
    assert result.output == "stub:Check the account state."


def test_model_runtime_service_normalizes_invalid_model_errors():
    class FakeOpenAIModelError(Exception):
        def __init__(self) -> None:
            super().__init__(
                "The model `planner-v1` does not exist or you do not have access to " "it."
            )
            self.code = "model_not_found"
            self.body = {
                "error": {
                    "message": (
                        "The model `planner-v1` does not exist or you do not have " "access to it."
                    ),
                    "code": "model_not_found",
                }
            }

    class ExplodingAdapter:
        def execute(
            self,
            *,
            api_key: SecretStr | None,
            model: str,
            prompt: str,
        ) -> RuntimeExecutionResult:
            raise FakeOpenAIModelError()

    service = ModelRuntimeService(adapters={AdapterKind.OPENAI_AGENTS: ExplodingAdapter()})
    service.api_key = SecretStr("sk-test")
    service.runtime_mode = "live"

    with pytest.raises(ModelNotFoundError) as exc_info:
        service.execute(
            AdapterKind.OPENAI_AGENTS,
            model="planner-v1",
            prompt="Summarize the ticket.",
        )

    assert exc_info.value.model == "planner-v1"
    assert exc_info.value.to_detail() == {
        "code": "model_not_found",
        "message": "model 'planner-v1' not found",
        "model": "planner-v1",
    }


def test_model_runtime_service_normalizes_invalid_model_errors_from_param_only_signal():
    class FakeBadRequestError(Exception):
        def __init__(self) -> None:
            super().__init__("Error code: 400")
            self.status_code = 400
            self.param = "model"
            self.body = {
                "error": {
                    "message": "Unknown model 'planner-v1'.",
                }
            }

    class ExplodingAdapter:
        def execute(
            self,
            *,
            api_key: SecretStr | None,
            model: str,
            prompt: str,
        ) -> RuntimeExecutionResult:
            raise FakeBadRequestError()

    service = ModelRuntimeService(adapters={AdapterKind.OPENAI_AGENTS: ExplodingAdapter()})
    service.api_key = SecretStr("sk-test")
    service.runtime_mode = "live"

    with pytest.raises(ModelNotFoundError):
        service.execute(
            AdapterKind.OPENAI_AGENTS,
            model="planner-v1",
            prompt="Summarize the ticket.",
        )


@pytest.mark.parametrize(
    ("status_code", "message", "expected_error"),
    [
        (401, "Invalid API key provided", ProviderAuthError),
        (429, "Rate limit exceeded for requests", RateLimitedError),
        (None, "The request timed out while waiting for the model response", ProviderTimeoutError),
    ],
)
def test_model_runtime_service_normalizes_runtime_provider_errors(
    status_code: int | None,
    message: str,
    expected_error: type[Exception],
):
    class ProviderError(Exception):
        def __init__(self) -> None:
            super().__init__(message)
            self.status_code = status_code

    class ExplodingAdapter:
        def execute(
            self,
            *,
            api_key: SecretStr | None,
            model: str,
            prompt: str,
        ) -> RuntimeExecutionResult:
            raise ProviderError()

    service = ModelRuntimeService(adapters={AdapterKind.OPENAI_AGENTS: ExplodingAdapter()})
    service.api_key = SecretStr("sk-test")
    service.runtime_mode = "live"

    with pytest.raises(expected_error):
        service.execute(
            AdapterKind.OPENAI_AGENTS,
            model="gpt-4.1-mini",
            prompt="Summarize the ticket.",
        )


def test_model_runtime_service_raises_structured_error_for_unsupported_adapter():
    service = ModelRuntimeService(adapters={})
    service.api_key = SecretStr("sk-test")
    service.runtime_mode = "live"

    with pytest.raises(UnsupportedAdapterError) as exc_info:
        service.execute(
            AdapterKind.MCP,
            model="gpt-4.1-mini",
            prompt="Summarize the ticket.",
        )

    assert exc_info.value.to_detail() == {
        "code": "unsupported_adapter",
        "message": "agent_type 'mcp' is not supported for live execution",
        "agent_type": "mcp",
    }
