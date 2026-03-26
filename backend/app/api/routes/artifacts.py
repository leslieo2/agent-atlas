from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from app.bootstrap.container import get_artifact_commands, get_artifact_queries
from app.modules.artifacts.api.schemas import ArtifactExportRequest, ArtifactMetadataResponse
from app.modules.artifacts.application.use_cases import ArtifactCommands, ArtifactQueries

router = APIRouter(prefix="/artifacts", tags=["artifacts"])


@router.get("", response_model=list[ArtifactMetadataResponse])
def list_artifacts(
    queries: Annotated[ArtifactQueries, Depends(get_artifact_queries)],
) -> list[ArtifactMetadataResponse]:
    return [ArtifactMetadataResponse.from_domain(artifact) for artifact in queries.list_artifacts()]


@router.post("/export", response_model=ArtifactMetadataResponse)
def create_artifact(
    payload: ArtifactExportRequest,
    commands: Annotated[ArtifactCommands, Depends(get_artifact_commands)],
) -> ArtifactMetadataResponse:
    if not payload.run_ids:
        raise HTTPException(status_code=400, detail="run_ids cannot be empty")
    artifact = commands.export(payload.to_domain())
    return ArtifactMetadataResponse.from_domain(artifact)


@router.get("/{artifact_id}")
def get_artifact(
    artifact_id: str,
    queries: Annotated[ArtifactQueries, Depends(get_artifact_queries)],
) -> FileResponse:
    from uuid import UUID

    try:
        artifact_uuid = UUID(artifact_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid artifact_id") from exc
    artifact = queries.get_artifact(artifact_uuid)
    if not artifact:
        raise HTTPException(status_code=404, detail="artifact not found")
    return FileResponse(
        artifact.path,
        filename=artifact.path.split("/")[-1],
        media_type="application/octet-stream",
    )
