from __future__ import annotations

from types import SimpleNamespace

from app.infrastructure.adapters.agents import (
    AgentModuleSource,
    FilesystemAgentDiscovery,
    FilesystemAgentSourceCatalog,
    OpenAIAgentContractValidator,
)
from app.modules.agents.domain.models import (
    AgentManifest,
    AgentValidationStatus,
    DiscoveredAgent,
)


def test_source_catalog_discovers_builtin_agent_plugins() -> None:
    sources = FilesystemAgentSourceCatalog().list_sources()

    assert {source.module_name for source in sources} >= {
        "app.agent_plugins.basic",
        "app.agent_plugins.customer_service",
        "app.agent_plugins.tools",
    }


def test_validator_reports_missing_manifest(monkeypatch) -> None:
    validator = OpenAIAgentContractValidator()
    module = SimpleNamespace(build_agent=lambda _context: object())

    monkeypatch.setattr(
        "app.infrastructure.adapters.agents.import_module",
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
            default_model="gpt-4.1-mini",
            tags=[],
        )
    )

    monkeypatch.setattr(
        "app.infrastructure.adapters.agents.import_module",
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
                    default_model="gpt-4.1-mini",
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
