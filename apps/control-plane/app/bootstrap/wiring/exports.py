from __future__ import annotations

from dataclasses import dataclass

from app.bootstrap.wiring.infrastructure import InfrastructureBundle
from app.modules.exports.adapters.outbound.filesystem.exporter import ExporterAdapter
from app.modules.exports.application.use_cases import ExportCommands, ExportQueries


@dataclass(frozen=True)
class ExportModuleBundle:
    exporter: ExporterAdapter
    export_queries: ExportQueries
    export_commands: ExportCommands


def build_export_module(infra: InfrastructureBundle) -> ExportModuleBundle:
    exporter = ExporterAdapter(
        export_repository=infra.export_repository,
        experiment_repository=infra.experiment_repository,
        run_evaluation_repository=infra.run_evaluation_repository,
    )
    export_queries = ExportQueries(export_repository=infra.export_repository)
    export_commands = ExportCommands(exporter=exporter)

    return ExportModuleBundle(
        exporter=exporter,
        export_queries=export_queries,
        export_commands=export_commands,
    )
