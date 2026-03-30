from __future__ import annotations

from app.bootstrap.container import get_container
from app.modules.exports.application.use_cases import ExportCommands, ExportQueries


def get_export_queries() -> ExportQueries:
    return get_container().exports.export_queries


def get_export_commands() -> ExportCommands:
    return get_container().exports.export_commands
