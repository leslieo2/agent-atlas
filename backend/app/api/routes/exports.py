from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from app.bootstrap.providers.exports import get_export_commands, get_export_queries
from app.modules.artifacts.application.use_cases import ArtifactCommands, ArtifactQueries
from app.modules.artifacts.contracts.schemas import ExportCreateRequest, ExportMetadataResponse

router = APIRouter(prefix="/exports", tags=["exports"])


@router.get("", response_model=list[ExportMetadataResponse])
def list_exports(
    queries: Annotated[ArtifactQueries, Depends(get_export_queries)],
) -> list[ExportMetadataResponse]:
    return [ExportMetadataResponse.from_domain(item) for item in queries.list_exports()]


@router.post("", response_model=ExportMetadataResponse)
def create_export(
    payload: ExportCreateRequest,
    commands: Annotated[ArtifactCommands, Depends(get_export_commands)],
) -> ExportMetadataResponse:
    if payload.experiment_id is None and payload.candidate_experiment_id is None:
        raise HTTPException(
            status_code=400,
            detail="export requires experiment_id or candidate_experiment_id",
        )
    try:
        artifact = commands.export(payload.to_domain())
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ExportMetadataResponse.from_domain(artifact)


@router.get("/{export_id}")
def get_export(
    export_id: str,
    queries: Annotated[ArtifactQueries, Depends(get_export_queries)],
) -> FileResponse:
    try:
        export_uuid = UUID(export_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid export_id") from exc
    artifact = queries.get_export(export_uuid)
    if not artifact:
        raise HTTPException(status_code=404, detail="export not found")
    return FileResponse(
        artifact.path,
        filename=artifact.path.split("/")[-1],
        media_type="application/octet-stream",
    )
