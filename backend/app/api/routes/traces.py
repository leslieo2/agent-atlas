from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.bootstrap.providers.runs import get_run_telemetry_ingestor
from app.bootstrap.providers.traces import get_trace_commands
from app.modules.runs.application.telemetry import RunTelemetryIngestionService
from app.modules.traces.application.use_cases import TraceCommands
from app.modules.traces.contracts.schemas import TraceIngestEvent

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
    ingestor: Annotated[RunTelemetryIngestionService, Depends(get_run_telemetry_ingestor)],
):
    event = ingestor.ingest(payload.to_domain())
    return {"status": "ok", "span_id": event.span_id}
