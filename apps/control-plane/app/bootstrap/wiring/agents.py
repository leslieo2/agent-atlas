from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from app.bootstrap.wiring.infrastructure import InfrastructureBundle
from app.modules.agents.application.ports import AgentValidationRecordPort
from app.modules.agents.application.use_cases import (
    AgentBootstrapCommands,
    AgentValidationCommands,
    PublishedAgentCatalogQueries,
)
from app.modules.agents.domain.models import AgentValidationRecord
from app.modules.runs.application.services import RunSubmissionService


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
    agent_bootstrap_commands: AgentBootstrapCommands
    agent_validation_commands: AgentValidationCommands


def build_agent_module(infra: InfrastructureBundle) -> AgentModuleBundle:
    validation_records: AgentValidationRecordPort = StateAgentValidationRecords(infra)

    def agent_exists(agent_id: str) -> bool:
        return infra.published_agent_catalog.get_agent(agent_id) is not None

    published_agent_catalog_queries = PublishedAgentCatalogQueries(
        published_agents=infra.published_agent_catalog,
        validation_records=validation_records,
    )
    agent_bootstrap_commands = AgentBootstrapCommands(
        published_agents=infra.published_agent_repository,
        live_agent_markers=infra.live_agent_marker_repository,
    )
    agent_validation_commands = AgentValidationCommands(
        published_agents=infra.published_agent_catalog,
        submission_service=RunSubmissionService(
            run_repository=infra.run_repository,
            execution_control=infra.execution.execution_control,
            default_trace_backend=infra.tracing.trace_backend.backend_name(),
        ),
    )

    return AgentModuleBundle(
        agent_exists=agent_exists,
        published_agent_catalog_queries=published_agent_catalog_queries,
        agent_bootstrap_commands=agent_bootstrap_commands,
        agent_validation_commands=agent_validation_commands,
    )
