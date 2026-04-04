from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from importlib import import_module
from importlib.metadata import entry_points
from typing import Any, Protocol, cast

from agent_atlas_contracts.execution import RunnerRunSpec
from pydantic import SecretStr

from app.core.errors import AgentFrameworkMismatchError, AgentLoadFailedError
from app.execution.application.results import PublishedRunExecutionResult
from app.modules.agents.domain.models import (
    AgentBuildContext,
    AgentManifest,
    AgentModuleSource,
    AgentValidationIssue,
    AgentValidationStatus,
    DiscoveredAgent,
    PublishedAgent,
    adapter_kind_for_agent_family,
)


class FrameworkDiscoveryValidator(Protocol):
    def discover(self, source: AgentModuleSource) -> DiscoveredAgent: ...


class PublishedAgentLoader(Protocol):
    def build_agent(
        self,
        *,
        published_agent: PublishedAgent,
        context: AgentBuildContext,
    ) -> Any: ...


class PublishedRuntimeExecutor(Protocol):
    def execute_published(
        self,
        *,
        api_key: SecretStr | None,
        payload: RunnerRunSpec,
        context: AgentBuildContext,
    ) -> PublishedRunExecutionResult: ...


@dataclass(frozen=True)
class FrameworkPlugin:
    framework: str
    validator: FrameworkDiscoveryValidator
    loader: PublishedAgentLoader
    runtime: PublishedRuntimeExecutor


FrameworkPluginBuilder = Callable[[], FrameworkPlugin]


class FrameworkRegistry:
    def __init__(self, plugins: Mapping[str, FrameworkPlugin]) -> None:
        self.plugins = {key.strip().lower(): value for key, value in plugins.items()}

    def discover(self, source: AgentModuleSource) -> DiscoveredAgent:
        framework = self._framework_for_source(source)
        if framework is None:
            return self._unresolved_framework(source)
        plugin = self.plugins.get(framework)
        if plugin is None:
            return self._unsupported_framework(source=source, framework=framework)
        return plugin.validator.discover(source)

    def build_agent(self, *, published_agent: PublishedAgent, context: AgentBuildContext) -> Any:
        plugin = self._plugin_for_framework(
            published_agent.framework,
            agent_id=published_agent.agent_id,
        )
        return plugin.loader.build_agent(published_agent=published_agent, context=context)

    def _plugin_for_framework(
        self,
        framework: str,
        *,
        agent_id: str | None = None,
    ) -> FrameworkPlugin:
        normalized = framework.strip().lower()
        plugin = self.plugins.get(normalized)
        if plugin is None:
            if agent_id is not None:
                raise AgentLoadFailedError(
                    f"published agent framework '{framework}' is not supported",
                    agent_id=agent_id,
                    framework=framework,
                )
            raise ValueError(f"unsupported published agent framework '{framework}'")
        return plugin

    @staticmethod
    def _framework_for_source(source: AgentModuleSource) -> str | None:
        module = FrameworkRegistry._safe_import(source.module_name)
        if module is None:
            return None

        raw_manifest = getattr(module, "AGENT_MANIFEST", None)
        if isinstance(raw_manifest, AgentManifest):
            framework = raw_manifest.framework.strip().lower()
            return framework or None

        if isinstance(raw_manifest, dict):
            raw_framework = raw_manifest.get("framework")
            if isinstance(raw_framework, str) and raw_framework.strip():
                return raw_framework.strip().lower()

        return None

    @staticmethod
    def _safe_import(module_name: str) -> Any | None:
        try:
            module = import_module(module_name)
        except Exception:
            return None
        return module

    @staticmethod
    def _unsupported_framework(source: AgentModuleSource, framework: str) -> DiscoveredAgent:
        module_leaf = source.module_name.rsplit(".", 1)[-1]
        return DiscoveredAgent(
            manifest=AgentManifest(
                agent_id=module_leaf,
                name=module_leaf.replace("_", " ").title(),
                description="Unsupported agent framework",
                framework=framework,
                default_model="",
                tags=[],
            ),
            entrypoint=source.entrypoint,
            validation_status=AgentValidationStatus.INVALID,
            validation_issues=[
                AgentValidationIssue(
                    code="framework_unsupported",
                    message=f"framework '{framework}' is not supported for discovery",
                )
            ],
        )

    @staticmethod
    def _unresolved_framework(source: AgentModuleSource) -> DiscoveredAgent:
        module_leaf = source.module_name.rsplit(".", 1)[-1]
        return DiscoveredAgent(
            manifest=AgentManifest(
                agent_id=module_leaf,
                name=module_leaf.replace("_", " ").title(),
                description="Agent framework metadata is missing or unreadable",
                framework="",
                default_model="",
                tags=[],
            ),
            entrypoint=source.entrypoint,
            validation_status=AgentValidationStatus.INVALID,
            validation_issues=[
                AgentValidationIssue(
                    code="framework_unresolved",
                    message=(
                        "agent framework could not be resolved from AGENT_MANIFEST; "
                        "Atlas no longer infers a builtin fallback framework"
                    ),
                )
            ],
        )


FRAMEWORK_PLUGIN_ENTRY_POINT_GROUP = "agent_atlas.framework_plugins"
BUILTIN_FRAMEWORK_PLUGIN_MODULES = (
    "app.infrastructure.adapters.claude_code",
    "app.infrastructure.adapters.openai_agents",
    "app.infrastructure.adapters.langchain",
)


def _load_plugin_builder_from_entry_point(plugin_entry: Any) -> FrameworkPluginBuilder | None:
    try:
        builder = plugin_entry.load()
    except Exception:
        return None
    if not callable(builder):
        return None
    return cast(FrameworkPluginBuilder, builder)


def _build_plugin(builder: FrameworkPluginBuilder) -> FrameworkPlugin | None:
    try:
        return builder()
    except Exception:
        return None


def discover_framework_plugins() -> dict[str, FrameworkPlugin]:
    plugins: dict[str, FrameworkPlugin] = {}
    for plugin_entry in entry_points().select(group=FRAMEWORK_PLUGIN_ENTRY_POINT_GROUP):
        builder = _load_plugin_builder_from_entry_point(plugin_entry)
        if builder is None:
            continue
        plugin = _build_plugin(builder)
        if plugin is None:
            continue
        plugins[plugin.framework.strip().lower()] = plugin

    for module_name in BUILTIN_FRAMEWORK_PLUGIN_MODULES:
        module = FrameworkRegistry._safe_import(module_name)
        if module is None:
            continue
        builder = getattr(module, "build_framework_plugin", None)
        if not callable(builder):
            continue
        plugin = _build_plugin(builder)
        if plugin is None:
            continue
        plugins.setdefault(plugin.framework.strip().lower(), plugin)

    return plugins


class PublishedAgentExecutionDispatcher:
    def __init__(self, plugins: Mapping[str, FrameworkPlugin]) -> None:
        self.plugins = {key.strip().lower(): value for key, value in plugins.items()}

    def execute_published(
        self,
        *,
        api_key: SecretStr | None,
        payload: RunnerRunSpec,
        context: AgentBuildContext,
    ) -> PublishedRunExecutionResult:
        try:
            published_agent = PublishedAgent.model_validate(payload.published_agent_snapshot)
        except Exception as exc:
            raise AgentLoadFailedError(
                "run payload is missing a valid published agent snapshot",
                agent_id=payload.agent_id,
            ) from exc

        expected_family = published_agent.agent_family
        expected_framework = published_agent.framework
        actual_framework = payload.framework
        actual_family = payload.framework_type or payload.agent_family
        if actual_family and actual_family.strip().lower() != expected_family.strip().lower():
            raise AgentFrameworkMismatchError(
                "run payload agent family does not match published snapshot",
                agent_id=payload.agent_id,
                expected_framework=expected_family,
                actual_framework=actual_family,
            )
        if actual_framework and (
            actual_framework.strip().lower() != expected_framework.strip().lower()
        ):
            raise AgentFrameworkMismatchError(
                "run payload framework metadata does not match published snapshot",
                agent_id=payload.agent_id,
                expected_framework=expected_framework,
                actual_framework=actual_framework,
            )

        expected_agent_type = adapter_kind_for_agent_family(expected_family)
        if payload.agent_type != expected_agent_type.value:
            raise AgentFrameworkMismatchError(
                "run payload adapter kind does not match published snapshot framework",
                agent_id=payload.agent_id,
                expected_framework=expected_framework,
                actual_agent_type=payload.agent_type,
            )

        if payload.agent_id and payload.agent_id != published_agent.agent_id:
            raise AgentFrameworkMismatchError(
                "run payload agent_id does not match published snapshot",
                agent_id=payload.agent_id,
                snapshot_agent_id=published_agent.agent_id,
            )

        plugin = self._plugin_for_framework(
            published_agent.framework,
            agent_id=published_agent.agent_id,
        )
        return plugin.runtime.execute_published(
            api_key=api_key,
            payload=payload,
            context=context,
        )

    def published_agent_from_payload(self, payload: RunnerRunSpec) -> PublishedAgent:
        try:
            published_agent = PublishedAgent.model_validate(payload.published_agent_snapshot)
        except Exception as exc:
            raise AgentLoadFailedError(
                "run payload is missing a valid published agent snapshot",
                agent_id=payload.agent_id,
            ) from exc

        expected_family = published_agent.agent_family
        expected_framework = published_agent.framework
        actual_framework = payload.framework
        actual_family = payload.framework_type or payload.agent_family
        if actual_family and actual_family.strip().lower() != expected_family.strip().lower():
            raise AgentFrameworkMismatchError(
                "run payload agent family does not match published snapshot",
                agent_id=payload.agent_id,
                expected_framework=expected_family,
                actual_framework=actual_family,
            )
        if actual_framework and (
            actual_framework.strip().lower() != expected_framework.strip().lower()
        ):
            raise AgentFrameworkMismatchError(
                "run payload framework metadata does not match published snapshot",
                agent_id=payload.agent_id,
                expected_framework=expected_framework,
                actual_framework=actual_framework,
            )

        expected_agent_type = adapter_kind_for_agent_family(expected_family)
        if payload.agent_type != expected_agent_type.value:
            raise AgentFrameworkMismatchError(
                "run payload adapter kind does not match published snapshot framework",
                agent_id=payload.agent_id,
                expected_framework=expected_framework,
                actual_agent_type=payload.agent_type,
            )

        if payload.agent_id and payload.agent_id != published_agent.agent_id:
            raise AgentFrameworkMismatchError(
                "run payload agent_id does not match published snapshot",
                agent_id=payload.agent_id,
                snapshot_agent_id=published_agent.agent_id,
            )

        return published_agent

    def _plugin_for_framework(
        self,
        framework: str,
        *,
        agent_id: str | None = None,
    ) -> FrameworkPlugin:
        normalized = framework.strip().lower()
        plugin = self.plugins.get(normalized)
        if plugin is None:
            if agent_id is not None:
                raise AgentLoadFailedError(
                    f"published agent framework '{framework}' is not supported",
                    agent_id=agent_id,
                    framework=framework,
                )
            raise ValueError(f"unsupported published agent framework '{framework}'")
        return plugin
