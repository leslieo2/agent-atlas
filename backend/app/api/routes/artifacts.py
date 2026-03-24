from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.db.state import state
from app.models.schemas import ArtifactExportRequest, ArtifactMetadata
from app.services.exporter import exporter

router = APIRouter(prefix="/artifacts", tags=["artifacts"])


@router.post("/export", response_model=ArtifactMetadata)
def create_artifact(payload: ArtifactExportRequest) -> ArtifactMetadata:
    if not payload.run_ids:
        raise HTTPException(status_code=400, detail="run_ids cannot be empty")
    return exporter.export(payload)


@router.get("/{artifact_id}")
def get_artifact(artifact_id: str) -> FileResponse:
    from uuid import UUID

    try:
        artifact_uuid = UUID(artifact_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid artifact_id") from exc
    artifact = state.artifacts.get(artifact_uuid)
    if not artifact:
        raise HTTPException(status_code=404, detail="artifact not found")
    return FileResponse(
        artifact.path,
        filename=artifact.path.split("/")[-1],
        media_type="application/octet-stream",
    )
