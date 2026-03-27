from __future__ import annotations

from app.bootstrap.container import get_container
from app.modules.artifacts.application.use_cases import ArtifactCommands, ArtifactQueries


def get_artifact_queries() -> ArtifactQueries:
    return get_container().artifacts.artifact_queries


def get_artifact_commands() -> ArtifactCommands:
    return get_container().artifacts.artifact_commands
