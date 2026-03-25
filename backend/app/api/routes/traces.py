from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.bootstrap.container import get_trace_commands
from app.modules.traces.api.schemas import TraceIngestEvent
from app.modules.traces.application.use_cases import TraceCommands

router = APIRouter(prefix="/traces", tags=["traces"])


@router.post("/normalize")
def normalize(
    payload: TraceIngestEvent,
    commands: Annotated[TraceCommands, Depends(get_trace_commands)],
):
    return commands.normalize(payload.to_domain())


@router.post("/ingest", status_code=201)
def ingest(
    payload: TraceIngestEvent,
    commands: Annotated[TraceCommands, Depends(get_trace_commands)],
):
    event = commands.ingest(payload.to_domain())
    return {"status": "ok", "span_id": event.span_id}
