from __future__ import annotations

from dataclasses import dataclass

from agent_atlas_contracts.runtime import (
    AgentManifest,
)
from agent_atlas_contracts.runtime import (
    ExecutionReferenceMetadata as ExecutionReference,
)
from app.modules.agents.domain.models import (
    GovernedPublishedAgent as PublishedAgent,
)
from app.modules.agents.domain.models import (
    compute_source_fingerprint,
)
from app.modules.shared.domain.enums import AgentFamily
from app.modules.shared.domain.models import build_source_execution_reference

FIXTURE_AGENT_MODULE_PREFIX = "tests.fixtures.agents"


@dataclass(frozen=True)
class FixtureAgentSource:
    agent_id: str
    module_name: str
    manifest: AgentManifest

    @property
    def entrypoint(self) -> str:
        return f"{self.module_name}:build_agent"


def _fixture_manifest(
    *,
    agent_id: str,
    name: str,
    description: str,
    default_model: str = "gpt-5.4-mini",
    tags: list[str] | None = None,
) -> AgentManifest:
    return AgentManifest(
        agent_id=agent_id,
        name=name,
        description=description,
        agent_family=AgentFamily.OPENAI_AGENTS.value,
        framework="openai-agents-sdk",
        default_model=default_model,
        tags=list(tags or []),
    )


def fixture_agent_source_catalog() -> list[FixtureAgentSource]:
    return [
        FixtureAgentSource(
            agent_id="basic",
            module_name=f"{FIXTURE_AGENT_MODULE_PREFIX}.basic",
            manifest=_fixture_manifest(
                agent_id="basic",
                name="Basic",
                description="Minimal fixture agent for Atlas execution smoke tests.",
                tags=["example", "smoke"],
            ),
        ),
        FixtureAgentSource(
            agent_id="customer_service",
            module_name=f"{FIXTURE_AGENT_MODULE_PREFIX}.customer_service",
            manifest=_fixture_manifest(
                agent_id="customer_service",
                name="Customer Service",
                description="Fixture support agent for policy-aware service guidance.",
                tags=["example", "support"],
            ),
        ),
        FixtureAgentSource(
            agent_id="tools",
            module_name=f"{FIXTURE_AGENT_MODULE_PREFIX}.tools",
            manifest=_fixture_manifest(
                agent_id="tools",
                name="Tools",
                description="Fixture agent with local tool calls for execution coverage.",
                tags=["example", "tools"],
            ),
        ),
        FixtureAgentSource(
            agent_id="fulfillment_ops",
            module_name=f"{FIXTURE_AGENT_MODULE_PREFIX}.fulfillment_ops",
            manifest=_fixture_manifest(
                agent_id="fulfillment_ops",
                name="Fulfillment Ops",
                description="Fixture order-fulfillment validation agent with multiple tools.",
                default_model="gpt-5-mini",
                tags=["example", "tools", "fulfillment"],
            ),
        ),
        FixtureAgentSource(
            agent_id="triage_bot",
            module_name=f"{FIXTURE_AGENT_MODULE_PREFIX}.triage_bot",
            manifest=_fixture_manifest(
                agent_id="triage_bot",
                name="Triage Bot",
                description="Fixture triage agent for run submission tests.",
                tags=["example", "triage"],
            ),
        ),
    ]


def fixture_agent_source_for_id(agent_id: str) -> FixtureAgentSource:
    for source in fixture_agent_source_catalog():
        if source.agent_id == agent_id:
            return source
    raise KeyError(f"unknown fixture agent '{agent_id}'")


def build_fixture_published_agent(agent_id: str) -> PublishedAgent:
    source = fixture_agent_source_for_id(agent_id)
    source_fingerprint = compute_source_fingerprint(source.manifest, source.entrypoint)
    execution_reference = ExecutionReference.model_validate(
        build_source_execution_reference(
            agent_id=source.agent_id,
            source_fingerprint=source_fingerprint,
        ).model_dump(mode="json")
    )
    return PublishedAgent.from_snapshot(
        {
            "manifest": source.manifest.model_dump(mode="json"),
            "entrypoint": source.entrypoint,
            "source_fingerprint": source_fingerprint,
            "execution_reference": execution_reference.model_dump(mode="json"),
        }
    )
