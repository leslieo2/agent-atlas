from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.db.state import state
from app.models.schemas import ReplayRequest, ReplayResult
from app.services.replay import replay_service

router = APIRouter(prefix="/replays", tags=["replays"])


@router.post("", status_code=status.HTTP_201_CREATED)
def create_replay(payload: ReplayRequest) -> ReplayResult:
    try:
        result = replay_service.replay_step(payload)
        return result
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{replay_id}")
def get_replay(replay_id: str) -> ReplayResult:
    from uuid import UUID
    try:
        replay_uuid = UUID(replay_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid replay_id") from exc
    result = state.replays.get(replay_uuid)
    if not result:
        raise HTTPException(status_code=404, detail="replay not found")
    return result
