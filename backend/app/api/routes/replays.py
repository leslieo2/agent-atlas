from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.bootstrap.container import get_replay_commands, get_replay_queries
from app.core.errors import AppError
from app.modules.replays.api.schemas import ReplayRequest, ReplayResponse
from app.modules.replays.application.use_cases import ReplayCommands, ReplayQueries

router = APIRouter(prefix="/replays", tags=["replays"])


@router.post("", response_model=ReplayResponse, status_code=status.HTTP_201_CREATED)
def create_replay(
    payload: ReplayRequest,
    commands: Annotated[ReplayCommands, Depends(get_replay_commands)],
) -> ReplayResponse:
    try:
        result = commands.replay_step(payload.to_domain())
        return ReplayResponse.from_domain(result)
    except KeyError as exc:
        detail = exc.args[0] if exc.args else "replay step not found"
        raise HTTPException(status_code=404, detail=detail) from exc
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.to_detail()) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{replay_id}", response_model=ReplayResponse)
def get_replay(
    replay_id: str,
    queries: Annotated[ReplayQueries, Depends(get_replay_queries)],
) -> ReplayResponse:
    from uuid import UUID

    try:
        replay_uuid = UUID(replay_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid replay_id") from exc
    result = queries.get_replay(replay_uuid)
    if not result:
        raise HTTPException(status_code=404, detail="replay not found")
    return ReplayResponse.from_domain(result)
