from __future__ import annotations

import sys
from types import ModuleType, SimpleNamespace

import pytest
from agent_atlas_contracts.execution import ExecutionArtifact, RunnerRunSpec
from agent_atlas_contracts.runtime import (
    AgentBuildContext,
    AgentManifest,
)
from agent_atlas_contracts.runtime import (
    ExecutionReferenceMetadata as ExecutionReference,
)
from app.core.errors import (
    AgentFrameworkMismatchError,
    ModelNotFoundError,
    ProviderAuthError,
    ProviderTimeoutError,
    RateLimitedError,
    UnsupportedAdapterError,
)
from app.execution.adapters import runner_run_spec_from_run_spec
from app.execution.application.results import (
    PublishedRunExecutionResult,
    RuntimeExecutionResult,
)
from app.infrastructure.adapters.framework_registry import (
    FrameworkPlugin,
    PublishedAgentExecutionDispatcher,
)
from app.infrastructure.adapters.langchain import PublishedLangChainAgentAdapter
from app.infrastructure.adapters.runtime import ModelRuntimeService
from app.modules.agents.domain.models import (
    PublishedAgent,
    compute_source_fingerprint,
)
from app.modules.runs.domain.models import RunExecutionSpec as ExecutionRunSpec
from app.modules.shared.domain.enums import AdapterKind
from app.modules.shared.domain.models import (
    ProvenanceMetadata,
    build_source_execution_reference,
)
from pydantic import SecretStr


def _artifact_for_agent(agent: PublishedAgent) -> ExecutionArtifact:
    source_fingerprint = agent.source_fingerprint_or_raise()
    execution_reference = agent.execution_reference_or_raise()
    return ExecutionArtifact(
        framework=agent.framework,
        entrypoint=agent.entrypoint,
        source_fingerprint=source_fingerprint,
        artifact_ref=execution_reference.artifact_ref,
        image_ref=execution_reference.image_ref,
        published_agent_snapshot=agent.to_snapshot(),
    )


def _seal_agent(agent: PublishedAgent) -> PublishedAgent:
    source_fingerprint = compute_source_fingerprint(agent.manifest, agent.entrypoint)
    execution_reference = ExecutionReference.model_validate(
        build_source_execution_reference(
            agent_id=agent.agent_id,
            source_fingerprint=source_fingerprint,
        ).model_dump(mode="json")
    )
    agent.source_fingerprint = source_fingerprint
    agent.execution_reference = execution_reference
    return agent


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

    result = service.execute(
        AdapterKind.LANGCHAIN,
        model="gpt-5.4-mini",
        prompt="Check the account state.",
    )

    assert adapter.calls == [("gpt-5.4-mini", "Check the account state.")]
    assert result.provider == "stub"
    assert result.output == "stub:Check the account state."


def test_model_runtime_service_loads_builtin_runtime_plugins(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    imported_modules: list[str] = []
    monkeypatch.setattr(
        "app.infrastructure.adapters.runtime.entry_points",
        lambda: SimpleNamespace(select=lambda **_kwargs: []),
    )
    monkeypatch.setattr(
        "app.infrastructure.adapters.runtime._import_runtime_plugin_module",
        lambda module_name: imported_modules.append(module_name) or None,
    )

    service = ModelRuntimeService()

    assert service.adapters == {}
    assert imported_modules == [
        "agent_atlas_runner_openai_agents.runtime_plugins",
        "agent_atlas_runner_langgraph.runtime_plugins",
    ]


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

    with pytest.raises(expected_error):
        service.execute(
            AdapterKind.OPENAI_AGENTS,
            model="gpt-5.4-mini",
            prompt="Summarize the ticket.",
        )


def test_model_runtime_service_raises_structured_error_for_unsupported_adapter():
    service = ModelRuntimeService(adapters={})
    service.api_key = SecretStr("sk-test")

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


def test_model_runtime_service_can_simulate_output_for_tests_without_api_key():
    service = ModelRuntimeService(adapters={}, simulate_outputs=True)
    service.api_key = None

    result = service.execute(
        AdapterKind.OPENAI_AGENTS,
        model="gpt-5.4-mini",
        prompt="Summarize the ticket.",
    )

    assert result.provider == "mock"
    assert "Simulated openai-agents-sdk execution" in result.output


def test_model_runtime_service_can_simulate_output_for_tests_with_api_key():
    service = ModelRuntimeService(adapters={}, simulate_outputs=True)
    service.api_key = SecretStr("sk-test")

    result = service.execute(
        AdapterKind.OPENAI_AGENTS,
        model="gpt-5.4-mini",
        prompt="Summarize the ticket.",
    )

    assert result.provider == "mock"
    assert "Simulated openai-agents-sdk execution" in result.output


def test_model_runtime_service_without_platform_key_defers_to_provider_adapter():
    class StubAdapter:
        def __init__(self) -> None:
            self.api_keys: list[SecretStr | None] = []

        def execute(
            self,
            *,
            api_key: SecretStr | None,
            model: str,
            prompt: str,
        ) -> RuntimeExecutionResult:
            self.api_keys.append(api_key)
            return RuntimeExecutionResult(
                output=f"provider:{prompt}",
                latency_ms=5,
                token_usage=1,
                provider="stub-provider",
                resolved_model=model,
            )

    adapter = StubAdapter()
    service = ModelRuntimeService(adapters={AdapterKind.LANGCHAIN: adapter})
    service.api_key = None

    result = service.execute(
        AdapterKind.LANGCHAIN,
        model="gpt-5.4-mini",
        prompt="Summarize the ticket.",
    )

    assert adapter.api_keys == [None]
    assert result.provider == "stub-provider"


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
            self.calls: list[tuple[str, SecretStr | None]] = []

        def execute_published(
            self,
            *,
            api_key: SecretStr | None,
            payload: RunnerRunSpec,
            context: AgentBuildContext,
        ) -> PublishedRunExecutionResult:
            self.calls.append((payload.agent_id, api_key))
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
    service.api_key = None
    published_agent = PublishedAgent(
        manifest=AgentManifest(
            agent_id="graph-bot",
            name="Graph Bot",
            description="LangGraph-backed agent",
            framework=AdapterKind.LANGCHAIN.value,
            default_model="gpt-5.4-mini",
            tags=[],
        ),
        entrypoint="tests.fixtures.agents.graph_bot:build_agent",
    )
    published_agent = _seal_agent(published_agent)
    payload = ExecutionRunSpec(
        project="migration-check",
        dataset="framework-ds",
        agent_id="graph-bot",
        model="gpt-5.4-mini",
        entrypoint="tests.fixtures.agents.graph_bot:build_agent",
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
        runner_run_spec_from_run_spec(
            payload,
            artifact=_artifact_for_agent(published_agent),
            runner_backend="local-process",
        ),
    )

    assert runtime.calls == [("graph-bot", None)]
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
        entrypoint="tests.fixtures.agents.graph_bot:build_agent",
    )
    published_agent = _seal_agent(published_agent)
    adapter = PublishedLangChainAgentAdapter(agent_loader=StubLoader())
    payload = ExecutionRunSpec(
        project="migration-check",
        dataset="framework-ds",
        agent_id="graph-bot",
        model="gpt-5.4-mini",
        entrypoint="tests.fixtures.agents.graph_bot:build_agent",
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
        payload=runner_run_spec_from_run_spec(
            payload,
            artifact=_artifact_for_agent(published_agent),
            runner_backend="local-process",
        ),
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
    service = ModelRuntimeService(
        adapters={},
        published_execution_dispatcher=dispatcher,
        simulate_outputs=True,
    )
    published_agent = PublishedAgent(
        manifest=AgentManifest(
            agent_id="graph-bot",
            name="Graph Bot",
            description="LangGraph-backed agent",
            framework=AdapterKind.LANGCHAIN.value,
            default_model="gpt-5.4-mini",
            tags=[],
        ),
        entrypoint="tests.fixtures.agents.graph_bot:build_agent",
    )
    published_agent = _seal_agent(published_agent)
    payload = ExecutionRunSpec(
        project="migration-check",
        dataset="framework-ds",
        agent_id="graph-bot",
        model="gpt-5.4-mini",
        entrypoint="tests.fixtures.agents.graph_bot:build_agent",
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
            runner_run_spec_from_run_spec(
                payload,
                artifact=_artifact_for_agent(published_agent),
                runner_backend="local-process",
            ),
        )

    payload.agent_type = AdapterKind.LANGCHAIN
    result = service.execute_published(
        "00000000-0000-0000-0000-000000000123",
        runner_run_spec_from_run_spec(
            payload,
            artifact=_artifact_for_agent(published_agent),
            runner_backend="local-process",
        ),
    )
    assert "Simulated langchain execution" in result.runtime_result.output
