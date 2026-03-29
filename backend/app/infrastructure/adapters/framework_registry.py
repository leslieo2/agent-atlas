from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from importlib import import_module
from typing import Any, Protocol

from pydantic import SecretStr

from app.core.errors import AgentLoadFailedError
from app.modules.agents.domain.models import (
    AgentBuildContext,
    AgentManifest,
    AgentModuleSource,
    AgentValidationIssue,
    AgentValidationStatus,
    DiscoveredAgent,
    PublishedAgent,
)
from app.modules.runs.application.results import PublishedRunExecutionResult
from app.modules.runs.domain.models import RunSpec
from app.modules.shared.domain.enums import AdapterKind


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
        payload: RunSpec,
        context: AgentBuildContext,
    ) -> PublishedRunExecutionResult: ...


@dataclass(frozen=True)
class FrameworkPlugin:
    framework: str
    validator: FrameworkDiscoveryValidator
    loader: PublishedAgentLoader
    runtime: PublishedRuntimeExecutor


class FrameworkRegistry:
    def __init__(self, plugins: Mapping[str, FrameworkPlugin]) -> None:
        self.plugins = {key.strip().lower(): value for key, value in plugins.items()}

    def discover(self, source: AgentModuleSource) -> DiscoveredAgent:
        framework = self._framework_for_source(source)
        plugin = self.plugins.get(framework)
        if plugin is None:
            return self._unsupported_framework(source=source, framework=framework)
        return plugin.validator.discover(source)

    def build_agent(self, *, published_agent: PublishedAgent, context: AgentBuildContext) -> Any:
        plugin = self._plugin_for_framework(published_agent.framework)
        return plugin.loader.build_agent(published_agent=published_agent, context=context)

    def execute_published(
        self,
        *,
        api_key: SecretStr | None,
        payload: RunSpec,
        context: AgentBuildContext,
    ) -> PublishedRunExecutionResult:
        try:
            snapshot = payload.provenance.published_agent_snapshot if payload.provenance else None
            published_agent = PublishedAgent.model_validate(snapshot)
        except Exception as exc:
            raise AgentLoadFailedError(
                "run payload is missing a valid published agent snapshot",
                agent_id=payload.agent_id,
            ) from exc

        plugin = self._plugin_for_framework(published_agent.framework)
        return plugin.runtime.execute_published(
            api_key=api_key,
            payload=payload,
            context=context,
        )

    def _plugin_for_framework(self, framework: str) -> FrameworkPlugin:
        normalized = framework.strip().lower()
        plugin = self.plugins.get(normalized)
        if plugin is None:
            raise ValueError(f"unsupported published agent framework '{framework}'")
        return plugin

    @staticmethod
    def _framework_for_source(source: AgentModuleSource) -> str:
        module = FrameworkRegistry._safe_import(source.module_name)
        if module is None:
            return AdapterKind.OPENAI_AGENTS.value

        raw_manifest = getattr(module, "AGENT_MANIFEST", None)
        if isinstance(raw_manifest, AgentManifest):
            return raw_manifest.framework.strip().lower()

        if isinstance(raw_manifest, dict):
            framework = raw_manifest.get("framework")
            if isinstance(framework, str) and framework.strip():
                return framework.strip().lower()

        return AdapterKind.OPENAI_AGENTS.value

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
