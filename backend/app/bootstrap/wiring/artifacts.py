from __future__ import annotations

from app.bootstrap.bundles import ArtifactModuleBundle, InfrastructureBundle
from app.infrastructure.adapters.artifacts import ArtifactExporterAdapter
from app.modules.artifacts.application.use_cases import ArtifactCommands, ArtifactQueries


def build_artifact_module(infra: InfrastructureBundle) -> ArtifactModuleBundle:
    artifact_exporter = ArtifactExporterAdapter(
        trajectory_repository=infra.trajectory_repository,
        artifact_repository=infra.artifact_repository,
        run_repository=infra.run_repository,
    )
    artifact_queries = ArtifactQueries(artifact_repository=infra.artifact_repository)
    artifact_commands = ArtifactCommands(artifact_exporter=artifact_exporter)

    return ArtifactModuleBundle(
        artifact_exporter=artifact_exporter,
        artifact_queries=artifact_queries,
        artifact_commands=artifact_commands,
    )
