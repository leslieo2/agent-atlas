from __future__ import annotations

from app.agent_tracing.application import RunTelemetryIngestionService
from app.bootstrap.container import get_container
from app.modules.runs.application.use_cases import RunCommands, RunQueries


def get_run_queries() -> RunQueries:
    return get_container().runs.run_queries


def get_run_commands() -> RunCommands:
    return get_container().runs.run_commands


def get_run_telemetry_ingestor() -> RunTelemetryIngestionService:
    return get_container().runs.telemetry_ingestor
