from __future__ import annotations

from types import SimpleNamespace

import pytest
from app.core.errors import AgentFrameworkMismatchError, AgentLoadFailedError
from app.execution.adapters import runner_run_spec_from_run_spec
from app.infrastructure.adapters.agent_catalog import (
    AgentModuleSource,
    FilesystemAgentDiscovery,
    FilesystemAgentSourceCatalog,
)
from app.infrastructure.adapters.framework_registry import (
    FrameworkPlugin,
    FrameworkRegistry,
    PublishedAgentExecutionDispatcher,
    discover_framework_plugins,
)
from app.infrastructure.adapters.langchain import LangChainAgentContractValidator
from app.infrastructure.adapters.openai_agents import (
    OpenAIAgentContractValidator,
)
from app.modules.agents.domain.models import (
    AgentBuildContext,
    AgentManifest,
    AgentValidationStatus,
    DiscoveredAgent,
    PublishedAgent,
)
from app.modules.runs.application.results import PublishedRunExecutionResult
from app.modules.runs.domain.models import RunSpec, RuntimeExecutionResult
from app.modules.shared.domain.enums import AdapterKind
from app.modules.shared.domain.models import ProvenanceMetadata


def test_source_catalog_discovers_builtin_agent_plugins() -> None:
    sources = FilesystemAgentSourceCatalog().list_sources()

    assert {source.module_name for source in sources} >= {
        "app.agent_plugins.basic",
        "app.agent_plugins.customer_service",
        "app.agent_plugins.fulfillment_ops",
        "app.agent_plugins.tools",
    }


def test_validator_reports_missing_manifest(monkeypatch) -> None:
    validator = OpenAIAgentContractValidator()
    module = SimpleNamespace(build_agent=lambda _context: object())

    monkeypatch.setattr(
        "app.infrastructure.adapters.openai_agents.catalog.import_module",
        lambda module_name: (
            module if module_name == "app.agent_plugins.fake_missing_manifest" else None
        ),
    )
    monkeypatch.setattr(
        validator,
        "_validate_build_agent",
        lambda **_kwargs: [],
    )

    discovered = validator.discover(
        AgentModuleSource(
            module_name="app.agent_plugins.fake_missing_manifest",
            entrypoint="app.agent_plugins.fake_missing_manifest:build_agent",
        )
    )

    assert discovered.validation_status == AgentValidationStatus.INVALID
    assert discovered.agent_id == "fake_missing_manifest"
    assert discovered.validation_issues[0].code == "manifest_missing"


def test_validator_reports_missing_build_agent(monkeypatch) -> None:
    validator = OpenAIAgentContractValidator()
    module = SimpleNamespace(
        AGENT_MANIFEST=AgentManifest(
            agent_id="fake",
            name="Fake",
            description="Fake plugin",
            default_model="gpt-5.4-mini",
            tags=[],
        )
    )

    monkeypatch.setattr(
        "app.infrastructure.adapters.openai_agents.catalog.import_module",
        lambda module_name: (
            module if module_name == "app.agent_plugins.fake_missing_build" else None
        ),
    )

    discovered = validator.discover(
        AgentModuleSource(
            module_name="app.agent_plugins.fake_missing_build",
            entrypoint="app.agent_plugins.fake_missing_build:build_agent",
        )
    )

    assert discovered.validation_status == AgentValidationStatus.INVALID
    assert [issue.code for issue in discovered.validation_issues] == ["build_agent_missing"]


def test_discovery_marks_duplicate_agent_ids_invalid() -> None:
    class StubSourceCatalog:
        def list_sources(self) -> list[AgentModuleSource]:
            return [
                AgentModuleSource("app.agent_plugins.first", "app.agent_plugins.first:build_agent"),
                AgentModuleSource(
                    "app.agent_plugins.second",
                    "app.agent_plugins.second:build_agent",
                ),
            ]

    class StubValidator:
        def discover(self, source: AgentModuleSource) -> DiscoveredAgent:
            return DiscoveredAgent(
                manifest=AgentManifest(
                    agent_id="duplicate",
                    name=source.module_name,
                    description="Duplicate plugin",
                    default_model="gpt-5.4-mini",
                    tags=[],
                ),
                entrypoint=source.entrypoint,
                validation_status=AgentValidationStatus.VALID,
                validation_issues=[],
            )

    discovery = FilesystemAgentDiscovery(
        source_catalog=StubSourceCatalog(),
        validator=StubValidator(),
    )

    discovered = discovery.list_agents()

    assert len(discovered) == 2
    assert all(agent.validation_status == AgentValidationStatus.INVALID for agent in discovered)
    assert all(
        any(issue.code == "duplicate_agent_id" for issue in agent.validation_issues)
        for agent in discovered
    )


def test_framework_registry_dispatches_discovery_by_manifest_framework(monkeypatch) -> None:
    module = SimpleNamespace(
        AGENT_MANIFEST=AgentManifest(
            agent_id="graph-bot",
            name="Graph Bot",
            description="LangGraph-backed agent",
            framework=AdapterKind.LANGCHAIN.value,
            default_model="gpt-5.4-mini",
            tags=[],
        )
    )
    monkeypatch.setattr(
        "app.infrastructure.adapters.framework_registry.import_module",
        lambda module_name: (module if module_name == "app.agent_plugins.graph_bot" else None),
    )

    class OpenAIValidator:
        def __init__(self) -> None:
            self.calls = 0

        def discover(self, source: AgentModuleSource) -> DiscoveredAgent:
            self.calls += 1
            raise AssertionError(f"unexpected dispatch for {source.module_name}")

    class LangChainValidator:
        def __init__(self) -> None:
            self.calls: list[str] = []

        def discover(self, source: AgentModuleSource) -> DiscoveredAgent:
            self.calls.append(source.module_name)
            return DiscoveredAgent(
                manifest=module.AGENT_MANIFEST,
                entrypoint=source.entrypoint,
                validation_status=AgentValidationStatus.VALID,
                validation_issues=[],
            )

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
            api_key,
            payload: RunSpec,
            context: AgentBuildContext,
        ) -> PublishedRunExecutionResult:
            del api_key, payload, context
            return PublishedRunExecutionResult(
                runtime_result=RuntimeExecutionResult(
                    output="ok",
                    latency_ms=1,
                    token_usage=0,
                    provider="stub",
                )
            )

    openai_validator = OpenAIValidator()
    langchain_validator = LangChainValidator()
    registry = FrameworkRegistry(
        plugins={
            AdapterKind.OPENAI_AGENTS.value: FrameworkPlugin(
                framework=AdapterKind.OPENAI_AGENTS.value,
                validator=openai_validator,
                loader=StubLoader(),
                runtime=StubRuntime(),
            ),
            AdapterKind.LANGCHAIN.value: FrameworkPlugin(
                framework=AdapterKind.LANGCHAIN.value,
                validator=langchain_validator,
                loader=StubLoader(),
                runtime=StubRuntime(),
            ),
        }
    )

    discovered = registry.discover(
        AgentModuleSource(
            module_name="app.agent_plugins.graph_bot",
            entrypoint="app.agent_plugins.graph_bot:build_agent",
        )
    )

    assert openai_validator.calls == 0
    assert langchain_validator.calls == ["app.agent_plugins.graph_bot"]
    assert discovered.framework == AdapterKind.LANGCHAIN.value


def test_framework_plugin_discovery_loads_package_manifests(monkeypatch) -> None:
    class StubEntryPoint:
        def __init__(self, builder) -> None:
            self._builder = builder

        def load(self):
            return self._builder

    plugin = FrameworkPlugin(
        framework=AdapterKind.LANGCHAIN.value,
        validator=SimpleNamespace(),
        loader=SimpleNamespace(),
        runtime=SimpleNamespace(),
    )

    monkeypatch.setattr(
        "app.infrastructure.adapters.framework_registry.entry_points",
        lambda: SimpleNamespace(
            select=lambda **kwargs: (
                [
                    StubEntryPoint(lambda: plugin),
                    StubEntryPoint(object()),
                ]
                if kwargs["group"] == "agent_atlas.framework_plugins"
                else []
            )
        ),
    )
    monkeypatch.setattr(
        "app.infrastructure.adapters.framework_registry.import_module",
        lambda module_name: (_ for _ in ()).throw(ImportError(module_name)),
    )

    discovered = discover_framework_plugins()

    assert discovered == {AdapterKind.LANGCHAIN.value: plugin}


def test_framework_plugin_discovery_falls_back_to_builtin_modules(monkeypatch) -> None:
    openai_plugin = FrameworkPlugin(
        framework=AdapterKind.OPENAI_AGENTS.value,
        validator=SimpleNamespace(),
        loader=SimpleNamespace(),
        runtime=SimpleNamespace(),
    )
    langchain_plugin = FrameworkPlugin(
        framework=AdapterKind.LANGCHAIN.value,
        validator=SimpleNamespace(),
        loader=SimpleNamespace(),
        runtime=SimpleNamespace(),
    )
    modules = {
        "app.infrastructure.adapters.openai_agents": SimpleNamespace(
            build_framework_plugin=lambda: openai_plugin
        ),
        "app.infrastructure.adapters.langchain": SimpleNamespace(
            build_framework_plugin=lambda: langchain_plugin
        ),
    }

    monkeypatch.setattr(
        "app.infrastructure.adapters.framework_registry.entry_points",
        lambda: SimpleNamespace(select=lambda **_kwargs: []),
    )
    monkeypatch.setattr(
        "app.infrastructure.adapters.framework_registry.import_module",
        lambda module_name: modules[module_name],
    )

    discovered = discover_framework_plugins()

    assert discovered == {
        AdapterKind.OPENAI_AGENTS.value: openai_plugin,
        AdapterKind.LANGCHAIN.value: langchain_plugin,
    }


def test_framework_plugin_discovery_skips_broken_entry_point_factories(monkeypatch) -> None:
    class StubEntryPoint:
        def __init__(self, builder) -> None:
            self._builder = builder

        def load(self):
            return self._builder

    plugin = FrameworkPlugin(
        framework=AdapterKind.LANGCHAIN.value,
        validator=SimpleNamespace(),
        loader=SimpleNamespace(),
        runtime=SimpleNamespace(),
    )

    monkeypatch.setattr(
        "app.infrastructure.adapters.framework_registry.entry_points",
        lambda: SimpleNamespace(
            select=lambda **kwargs: (
                [
                    StubEntryPoint(lambda: (_ for _ in ()).throw(RuntimeError("broken factory"))),
                    StubEntryPoint(lambda: plugin),
                ]
                if kwargs["group"] == "agent_atlas.framework_plugins"
                else []
            )
        ),
    )
    monkeypatch.setattr(
        "app.infrastructure.adapters.framework_registry.import_module",
        lambda module_name: (_ for _ in ()).throw(ImportError(module_name)),
    )

    discovered = discover_framework_plugins()

    assert discovered == {AdapterKind.LANGCHAIN.value: plugin}


def test_langchain_validator_accepts_invoke_based_runnable(monkeypatch) -> None:
    validator = LangChainAgentContractValidator()

    class RunnableGraph:
        def invoke(self, payload: object) -> dict[str, str]:
            del payload
            return {"output": "graph response"}

    module = SimpleNamespace(
        AGENT_MANIFEST=AgentManifest(
            agent_id="graph-bot",
            name="Graph Bot",
            description="LangGraph-backed agent",
            framework=AdapterKind.LANGCHAIN.value,
            default_model="gpt-5.4-mini",
            tags=[],
        ),
        build_agent=lambda _context: RunnableGraph(),
    )
    monkeypatch.setattr(
        "app.infrastructure.adapters.langchain.catalog.import_module",
        lambda module_name: (module if module_name == "app.agent_plugins.graph_bot" else None),
    )

    discovered = validator.discover(
        AgentModuleSource(
            module_name="app.agent_plugins.graph_bot",
            entrypoint="app.agent_plugins.graph_bot:build_agent",
        )
    )

    assert discovered.validation_status == AgentValidationStatus.VALID
    assert discovered.framework == AdapterKind.LANGCHAIN.value


def test_framework_registry_rejects_published_payload_framework_mismatch() -> None:
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
        def execute_published(self, *, api_key, payload: RunSpec, context: AgentBuildContext):
            del api_key, payload, context
            raise AssertionError("runtime should not be called when framework metadata is invalid")

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
        provenance=ProvenanceMetadata(
            framework=AdapterKind.OPENAI_AGENTS.value,
            published_agent_snapshot=published_agent.to_snapshot(),
        ),
    )

    with pytest.raises(AgentFrameworkMismatchError):
        dispatcher.execute_published(
            api_key=None,
            payload=runner_run_spec_from_run_spec(payload),
            context=AgentBuildContext(
                run_id="00000000-0000-0000-0000-000000000123",
                project="migration-check",
                dataset="framework-ds",
                prompt="Inspect the latest run.",
                tags=[],
                project_metadata={},
            ),
        )


def test_framework_registry_rejects_unsupported_published_framework() -> None:
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
        def execute_published(self, *, api_key, payload: RunSpec, context: AgentBuildContext):
            del api_key, payload, context
            return PublishedRunExecutionResult(
                runtime_result=RuntimeExecutionResult(
                    output="ok",
                    latency_ms=1,
                    token_usage=0,
                    provider="stub",
                )
            )

    dispatcher = PublishedAgentExecutionDispatcher(
        plugins={
            AdapterKind.OPENAI_AGENTS.value: FrameworkPlugin(
                framework=AdapterKind.OPENAI_AGENTS.value,
                validator=StubValidator(),
                loader=StubLoader(),
                runtime=StubRuntime(),
            )
        }
    )
    published_agent = PublishedAgent(
        manifest=AgentManifest(
            agent_id="graph-bot",
            name="Graph Bot",
            description="Unsupported runtime",
            framework=AdapterKind.MCP.value,
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
        agent_type=AdapterKind.MCP,
        input_summary="framework coverage",
        prompt="Inspect the latest run.",
        provenance=ProvenanceMetadata(
            framework=AdapterKind.MCP.value,
            published_agent_snapshot=published_agent.to_snapshot(),
        ),
    )

    with pytest.raises(
        AgentLoadFailedError,
        match="published agent framework 'mcp' is not supported",
    ):
        dispatcher.execute_published(
            api_key=None,
            payload=runner_run_spec_from_run_spec(payload),
            context=AgentBuildContext(
                run_id="00000000-0000-0000-0000-000000000123",
                project="migration-check",
                dataset="framework-ds",
                prompt="Inspect the latest run.",
                tags=[],
                project_metadata={},
            ),
        )
