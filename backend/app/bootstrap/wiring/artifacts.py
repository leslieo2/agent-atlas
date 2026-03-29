from __future__ import annotations

from dataclasses import dataclass

from app.bootstrap.wiring.infrastructure import InfrastructureBundle
from app.infrastructure.adapters.artifacts import ArtifactExporterAdapter
from app.modules.artifacts.application.use_cases import ArtifactCommands, ArtifactQueries


@dataclass(frozen=True)
class ArtifactModuleBundle:
    artifact_exporter: ArtifactExporterAdapter
    artifact_queries: ArtifactQueries
    artifact_commands: ArtifactCommands


def build_artifact_module(infra: InfrastructureBundle) -> ArtifactModuleBundle:
    artifact_exporter = ArtifactExporterAdapter(
        artifact_repository=infra.artifact_repository,
        experiment_repository=infra.experiment_repository,
        run_evaluation_repository=infra.run_evaluation_repository,
    )
    artifact_queries = ArtifactQueries(artifact_repository=infra.artifact_repository)
    artifact_commands = ArtifactCommands(artifact_exporter=artifact_exporter)

    return ArtifactModuleBundle(
        artifact_exporter=artifact_exporter,
        artifact_queries=artifact_queries,
        artifact_commands=artifact_commands,
    )
