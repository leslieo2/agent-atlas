from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from app.bootstrap.wiring.infrastructure import InfrastructureBundle
from app.core.config import RuntimeMode, settings
from app.modules.agents.application.ports import AgentValidationRecordPort
from app.modules.agents.application.use_cases import (
    AgentDiscoveryQueries,
    AgentPublicationCommands,
    PublishedAgentCatalogQueries,
)
from app.modules.agents.domain.models import AgentValidationRecord


class StateAgentValidationRecords:
    def __init__(self, infra: InfrastructureBundle) -> None:
        self.run_repository = infra.run_repository

    def list_records(self) -> list[AgentValidationRecord]:
        records: list[AgentValidationRecord] = []
        for run in self.run_repository.list():
            if "validation" not in set(run.tags) or not run.agent_id:
                continue
            trace_url = None
            if (
                run.trace_pointer is not None
                and isinstance(run.trace_pointer.trace_url, str)
                and run.trace_pointer.trace_url.strip()
            ):
                trace_url = run.trace_pointer.trace_url.strip()
            elif (
                run.tracing is not None
                and isinstance(run.tracing.trace_url, str)
                and run.tracing.trace_url.strip()
            ):
                trace_url = run.tracing.trace_url.strip()

            terminal_summary = None
            for candidate in (
                run.error_message,
                run.terminal_reason,
                run.termination_reason,
                run.error_code,
            ):
                if isinstance(candidate, str) and candidate.strip():
                    terminal_summary = candidate.strip()
                    break

            records.append(
                AgentValidationRecord(
                    agent_id=run.agent_id,
                    run_id=run.run_id,
                    status=run.status,
                    created_at=run.created_at,
                    started_at=run.started_at,
                    completed_at=run.completed_at,
                    artifact_ref=run.artifact_ref,
                    image_ref=run.image_ref,
                    trace_url=trace_url,
                    terminal_summary=terminal_summary,
                )
            )
        return records


@dataclass(frozen=True)
class AgentModuleBundle:
    agent_exists: Callable[[str], bool]
    published_agent_catalog_queries: PublishedAgentCatalogQueries
    agent_discovery_queries: AgentDiscoveryQueries
    agent_publication_commands: AgentPublicationCommands


def build_agent_module(infra: InfrastructureBundle) -> AgentModuleBundle:
    live_mode = settings.effective_runtime_mode() == RuntimeMode.LIVE
    validation_records: AgentValidationRecordPort = StateAgentValidationRecords(infra)

    def agent_exists(agent_id: str) -> bool:
        if live_mode:
            return infra.published_agent_repository.get_agent(agent_id) is not None
        return infra.published_agent_catalog.get_agent(agent_id) is not None

    published_agent_catalog_queries = PublishedAgentCatalogQueries(
        published_agents=(
            infra.published_agent_repository if live_mode else infra.published_agent_catalog
        ),
        validation_records=validation_records,
    )
    agent_discovery_queries = AgentDiscoveryQueries(
        discovery=None if live_mode else infra.agent_discovery,
        published_agents=infra.published_agent_repository,
        validation_records=validation_records,
    )
    agent_publication_commands = AgentPublicationCommands(
        discovery=None if live_mode else infra.agent_discovery,
        published_agents=infra.published_agent_repository,
    )

    return AgentModuleBundle(
        agent_exists=agent_exists,
        published_agent_catalog_queries=published_agent_catalog_queries,
        agent_discovery_queries=agent_discovery_queries,
        agent_publication_commands=agent_publication_commands,
    )
