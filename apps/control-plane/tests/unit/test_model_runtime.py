from __future__ import annotations

import sys
from types import ModuleType, SimpleNamespace

import pytest
from agent_atlas_contracts.execution import RunnerRunSpec
from app.core.config import RuntimeMode
from app.core.errors import (
    AgentFrameworkMismatchError,
    ModelNotFoundError,
    ProviderAuthError,
    ProviderTimeoutError,
    RateLimitedError,
    UnsupportedAdapterError,
)
from app.infrastructure.adapters.framework_registry import (
    FrameworkPlugin,
    FrameworkRegistry,
    PublishedAgentExecutionDispatcher,
)
from app.infrastructure.adapters.langchain.runtime import PublishedLangChainAgentAdapter
from app.infrastructure.adapters.runtime import ModelRuntimeService
from app.modules.agents.domain.models import AgentBuildContext, AgentManifest, PublishedAgent
from app.modules.runs.adapters.outbound.execution import runner_run_spec_from_run_spec
from app.modules.runs.application.results import PublishedRunExecutionResult
from app.modules.runs.domain.models import RunSpec, RuntimeExecutionResult
from app.modules.shared.domain.enums import AdapterKind
from app.modules.shared.domain.models import ProvenanceMetadata
from pydantic import SecretStr


def test_model_runtime_service_uses_openai_agents_sdk_runner(monkeypatch: pytest.MonkeyPatch):
    calls: dict[str, object] = {}
    fake_agents = ModuleType("agents")

    class Agent:
        def __init__(self, *, name: str, instructions: str, model: str) -> None:
            calls["agent"] = {
                "name": name,
                "instructions": instructions,
                "model": model,
            }

    class Runner:
        @staticmethod
        def run_sync(
            agent: Agent,
            prompt: str,
            *,
            run_config: object | None = None,
        ) -> SimpleNamespace:
            calls["run_sync"] = {"agent": agent, "prompt": prompt, "run_config": run_config}
            calls["model_provider"] = getattr(run_config, "model_provider", None)
            usage = SimpleNamespace(total_tokens=123)
            context_wrapper = SimpleNamespace(usage=usage)
            return SimpleNamespace(final_output="sdk output", context_wrapper=context_wrapper)

    class OpenAIProvider:
        def __init__(self, *, api_key: str | None = None) -> None:
            self._stored_api_key = api_key

    class RunConfig:
        def __init__(self, *, model_provider: object) -> None:
            self.model_provider = model_provider

    fake_agents.Agent = Agent
    fake_agents.Runner = Runner
    fake_agents.OpenAIProvider = OpenAIProvider
    fake_agents.RunConfig = RunConfig
    monkeypatch.setitem(sys.modules, "agents", fake_agents)

    service = ModelRuntimeService()
    service.api_key = SecretStr("sk-test")
    service.runtime_mode = RuntimeMode.LIVE

    result = service.execute(
        AdapterKind.OPENAI_AGENTS,
        model="gpt-5.4-mini",
        prompt="Summarize the ticket.",
    )

    assert calls["agent"] == {
        "name": "Agent Atlas Assistant",
        "instructions": (
            "You are a concise assistant inside Agent Atlas. " "Return the best direct answer."
        ),
        "model": "gpt-5.4-mini",
    }
    assert calls["run_sync"]["prompt"] == "Summarize the ticket."
    assert calls["model_provider"]._stored_api_key == "sk-test"
    assert result == RuntimeExecutionResult(
        output="sdk output",
        latency_ms=result.latency_ms,
        token_usage=123,
        provider="openai-agents-sdk",
        resolved_model="gpt-5.4-mini",
    )
    assert result.latency_ms >= 0


def test_model_runtime_service_raises_clear_error_when_agents_sdk_missing():
    sys.modules.pop("agents", None)
    sys.modules["agents"] = None
    service = ModelRuntimeService()
    service.api_key = SecretStr("sk-test")
    service.runtime_mode = RuntimeMode.LIVE

    try:
        with pytest.raises(
            RuntimeError,
            match="OpenAI Agents SDK package 'agents' is not installed",
        ):
            service.execute(
                AdapterKind.OPENAI_AGENTS,
                model="gpt-5.4-mini",
                prompt="Summarize the ticket.",
            )
    finally:
        sys.modules.pop("agents", None)


def test_model_runtime_service_dispatches_through_runtime_adapters():
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
    service.runtime_mode = RuntimeMode.LIVE

    result = service.execute(
        AdapterKind.LANGCHAIN,
        model="gpt-5.4-mini",
        prompt="Check the account state.",
    )

    assert adapter.calls == [("gpt-5.4-mini", "Check the account state.")]
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
    service.runtime_mode = RuntimeMode.LIVE

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
    service.runtime_mode = RuntimeMode.LIVE

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
    service.runtime_mode = RuntimeMode.LIVE

    with pytest.raises(expected_error):
        service.execute(
            AdapterKind.OPENAI_AGENTS,
            model="gpt-5.4-mini",
            prompt="Summarize the ticket.",
        )


def test_model_runtime_service_raises_structured_error_for_unsupported_adapter():
    service = ModelRuntimeService(adapters={})
    service.api_key = SecretStr("sk-test")
    service.runtime_mode = RuntimeMode.LIVE

    with pytest.raises(UnsupportedAdapterError) as exc_info:
        service.execute(
            AdapterKind.MCP,
            model="gpt-5.4-mini",
            prompt="Summarize the ticket.",
        )

    assert exc_info.value.to_detail() == {
        "code": "unsupported_adapter",
        "message": "agent_type 'mcp' is not supported for live execution",
        "agent_type": "mcp",
    }


def test_model_runtime_service_auto_mode_without_key_uses_mock():
    service = ModelRuntimeService(adapters={})
    service.api_key = None
    service.runtime_mode = RuntimeMode.AUTO

    result = service.execute(
        AdapterKind.OPENAI_AGENTS,
        model="gpt-5.4-mini",
        prompt="Summarize the ticket.",
    )

    assert result.provider == "mock"
    assert "Simulated openai-agents-sdk execution" in result.output


def test_model_runtime_service_live_mode_without_key_raises():
    service = ModelRuntimeService(adapters={})
    service.api_key = None
    service.runtime_mode = RuntimeMode.LIVE

    with pytest.raises(RuntimeError, match="OPENAI_API_KEY is not set"):
        service.execute(
            AdapterKind.OPENAI_AGENTS,
            model="gpt-5.4-mini",
            prompt="Summarize the ticket.",
        )


def test_model_runtime_service_dispatches_published_runs_through_execution_dispatcher():
    class StubValidator:
        def discover(self, source):
            raise AssertionError(f"unexpected discovery: {source}")

    class StubLoader:
        def build_agent(
            self,
            *,
            published_agent: PublishedAgent,
            context: AgentBuildContext,
        ) -> object:
            del published_agent, context
            return object()

    class LangChainRuntime:
        def __init__(self) -> None:
            self.calls: list[str] = []

        def execute_published(
            self,
            *,
            api_key: SecretStr | None,
            payload: RunnerRunSpec,
            context: AgentBuildContext,
        ) -> PublishedRunExecutionResult:
            assert api_key is not None
            self.calls.append(payload.agent_id)
            assert context.project == payload.project
            return PublishedRunExecutionResult(
                runtime_result=RuntimeExecutionResult(
                    output="registry-dispatch",
                    latency_ms=3,
                    token_usage=5,
                    provider="langchain",
                    execution_backend="langgraph",
                    resolved_model=payload.model,
                )
            )

    runtime = LangChainRuntime()
    dispatcher = PublishedAgentExecutionDispatcher(
        plugins={
            AdapterKind.LANGCHAIN.value: FrameworkPlugin(
                framework=AdapterKind.LANGCHAIN.value,
                validator=StubValidator(),
                loader=StubLoader(),
                runtime=runtime,
            )
        }
    )
    service = ModelRuntimeService(adapters={}, published_execution_dispatcher=dispatcher)
    service.api_key = SecretStr("sk-test")
    service.runtime_mode = RuntimeMode.LIVE
    published_agent = PublishedAgent(
        manifest=AgentManifest(
            agent_id="graph-bot",
            name="Graph Bot",
            description="LangGraph-backed agent",
            framework=AdapterKind.LANGCHAIN.value,
            default_model="gpt-5.4-mini",
            tags=[],
        ),
        entrypoint="app.agent_plugins.graph_bot:build_agent",
    )
    payload = RunSpec(
        project="migration-check",
        dataset="framework-ds",
        agent_id="graph-bot",
        model="gpt-5.4-mini",
        entrypoint="app.agent_plugins.graph_bot:build_agent",
        agent_type=AdapterKind.LANGCHAIN,
        input_summary="framework coverage",
        prompt="Inspect the latest run.",
        tags=["langchain"],
        provenance=ProvenanceMetadata(
            framework=AdapterKind.LANGCHAIN.value,
            published_agent_snapshot=published_agent.to_snapshot(),
        ),
    )

    result = service.execute_published(
        "00000000-0000-0000-0000-000000000123",
        runner_run_spec_from_run_spec(payload),
    )

    assert runtime.calls == ["graph-bot"]
    assert result.runtime_result.execution_backend == "langgraph"
    assert result.runtime_result.provider == "langchain"


def test_published_langchain_agent_adapter_executes_invoke_graph():
    class StubLoader:
        def build_agent(
            self,
            *,
            published_agent: PublishedAgent,
            context: AgentBuildContext,
        ) -> object:
            del published_agent, context

            class RunnableGraph:
                def invoke(self, payload: object) -> dict[str, object]:
                    assert isinstance(payload, dict)
                    return {
                        "output": "graph response",
                        "usage": {"total_tokens": 21},
                    }

            return RunnableGraph()

    published_agent = PublishedAgent(
        manifest=AgentManifest(
            agent_id="graph-bot",
            name="Graph Bot",
            description="LangGraph-backed agent",
            framework=AdapterKind.LANGCHAIN.value,
            default_model="gpt-5.4-mini",
            tags=[],
        ),
        entrypoint="app.agent_plugins.graph_bot:build_agent",
    )
    adapter = PublishedLangChainAgentAdapter(agent_loader=StubLoader())
    payload = RunSpec(
        project="migration-check",
        dataset="framework-ds",
        agent_id="graph-bot",
        model="gpt-5.4-mini",
        entrypoint="app.agent_plugins.graph_bot:build_agent",
        agent_type=AdapterKind.LANGCHAIN,
        input_summary="framework coverage",
        prompt="Inspect the latest run.",
        tags=["langchain"],
        provenance=ProvenanceMetadata(
            framework=AdapterKind.LANGCHAIN.value,
            published_agent_snapshot=published_agent.to_snapshot(),
        ),
    )
    context = AgentBuildContext(
        run_id="00000000-0000-0000-0000-000000000111",
        project="migration-check",
        dataset="framework-ds",
        prompt="Inspect the latest run.",
        tags=["langchain"],
        project_metadata=payload.project_metadata,
    )

    result = adapter.execute_published(
        api_key=SecretStr("sk-test"),
        payload=runner_run_spec_from_run_spec(payload),
        context=context,
    )

    assert result.runtime_result.output == "graph response"
    assert result.runtime_result.provider == "langchain"
    assert result.runtime_result.execution_backend == "langgraph"
    assert result.runtime_result.token_usage == 21
    assert len(result.event_envelopes) == 1
    assert len(result.projected_trace_events()) == 1
    assert result.projected_trace_events()[0].step_type.value == "llm"
    assert result.terminal_result is not None
    assert result.terminal_result.status == "succeeded"


def test_model_runtime_service_mock_mode_uses_snapshot_framework_for_published_runs():
    class StubValidator:
        def discover(self, source):
            raise AssertionError(f"unexpected discovery: {source}")

    class StubLoader:
        def build_agent(
            self,
            *,
            published_agent: PublishedAgent,
            context: AgentBuildContext,
        ) -> object:
            del published_agent, context
            return object()

    class StubRuntime:
        def execute_published(
            self,
            *,
            api_key: SecretStr | None,
            payload: RunnerRunSpec,
            context: AgentBuildContext,
        ) -> PublishedRunExecutionResult:
            del api_key, payload, context
            raise AssertionError("mock mode should not call live runtime")

    dispatcher = PublishedAgentExecutionDispatcher(
        plugins={
            AdapterKind.LANGCHAIN.value: FrameworkPlugin(
                framework=AdapterKind.LANGCHAIN.value,
                validator=StubValidator(),
                loader=StubLoader(),
                runtime=StubRuntime(),
            )
        }
    )
    service = ModelRuntimeService(adapters={}, published_execution_dispatcher=dispatcher)
    service.runtime_mode = RuntimeMode.MOCK
    published_agent = PublishedAgent(
        manifest=AgentManifest(
            agent_id="graph-bot",
            name="Graph Bot",
            description="LangGraph-backed agent",
            framework=AdapterKind.LANGCHAIN.value,
            default_model="gpt-5.4-mini",
            tags=[],
        ),
        entrypoint="app.agent_plugins.graph_bot:build_agent",
    )
    payload = RunSpec(
        project="migration-check",
        dataset="framework-ds",
        agent_id="graph-bot",
        model="gpt-5.4-mini",
        entrypoint="app.agent_plugins.graph_bot:build_agent",
        agent_type=AdapterKind.OPENAI_AGENTS,
        input_summary="framework coverage",
        prompt="Inspect the latest run.",
        tags=["langchain"],
        provenance=ProvenanceMetadata(
            framework=AdapterKind.LANGCHAIN.value,
            published_agent_snapshot=published_agent.to_snapshot(),
        ),
    )

    with pytest.raises(AgentFrameworkMismatchError):
        service.execute_published(
            "00000000-0000-0000-0000-000000000123",
            runner_run_spec_from_run_spec(payload),
        )

    payload.agent_type = AdapterKind.LANGCHAIN
    result = service.execute_published(
        "00000000-0000-0000-0000-000000000123",
        runner_run_spec_from_run_spec(payload),
    )
    assert "Simulated langchain execution" in result.runtime_result.output
