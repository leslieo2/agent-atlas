from __future__ import annotations

from fastapi import APIRouter

from app.models.schemas import TraceIngestEvent
from app.services.adapter import adapter_manager
from app.services.trace import trace_gateway

router = APIRouter(prefix="/traces", tags=["traces"])


@router.post("/normalize")
def normalize(payload: TraceIngestEvent):
    event = trace_gateway.ingest(payload)
    return adapter_manager.normalize_span(event.run_id, event)


@router.post("/ingest", status_code=201)
def ingest(payload: TraceIngestEvent):
    event = trace_gateway.ingest(payload)
    return {"status": "ok", "span_id": event.span_id}
