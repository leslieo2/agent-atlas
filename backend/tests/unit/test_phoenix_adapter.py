from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from app.bootstrap.wiring.infrastructure import build_infrastructure
from app.core.config import settings
from app.infrastructure.adapters.phoenix import (
    PhoenixTraceBackend,
    build_phoenix_project_url,
    build_phoenix_trace_url,
)
from app.modules.runs.domain.models import RunRecord


class _RunRepository:
    def __init__(self, run: RunRecord) -> None:
        self.run = run

    def get(self, run_id):
        return self.run if str(self.run.run_id) == str(run_id) else None


def test_build_phoenix_urls():
    project_url = build_phoenix_project_url(
        base_url="http://phoenix.local:6006/",
        project_name="atlas-control-plane",
        eval_job_id="job-123",
        run_id="run-456",
    )
    trace_url = build_phoenix_trace_url(
        base_url="http://phoenix.local:6006/",
        project_name="atlas-control-plane",
        trace_id="abc123",
    )

    assert project_url == (
        "http://phoenix.local:6006/projects/atlas-control-plane?"
        "eval_job_id=job-123&run_id=run-456"
    )
    assert trace_url == "http://phoenix.local:6006/projects/atlas-control-plane/traces/abc123"


def test_phoenix_trace_backend_filters_and_maps_run_spans():
    run_id = uuid4()
    run = RunRecord(
        run_id=run_id,
        input_summary="phoenix trace",
        project="control-plane",
        model="gpt-5.4-mini",
        agent_type="openai-agents-sdk",
        created_at=datetime(2026, 3, 29, 8, 0, tzinfo=UTC),
    )
    raw_span = {
        "id": "phoenix-span-1",
        "start_time": "2026-03-29T08:00:01+00:00",
        "end_time": "2026-03-29T08:00:02+00:00",
        "attributes": {
            "atlas.run_id": str(run_id),
            "atlas.span_id": "span-1",
            "atlas.parent_span_id": None,
            "atlas.step_type": "llm",
            "atlas.tool_name": None,
            "atlas.latency_ms": 17,
            "atlas.token_usage": 31,
            "atlas.image_digest": "sha256:test",
            "atlas.prompt_version": "v2",
            "atlas.input_json": '{"prompt": "hello"}',
            "atlas.output_json": '{"output": "world"}',
            "atlas.received_at": "2026-03-29T08:00:02+00:00",
        },
    }
    other_span = {
        "id": "phoenix-span-2",
        "start_time": "2026-03-29T08:00:03+00:00",
        "attributes": {
            "atlas.run_id": str(uuid4()),
        },
    }

    backend = object.__new__(PhoenixTraceBackend)
    backend.run_repository = _RunRepository(run)
    backend.client = SimpleNamespace(
        spans=SimpleNamespace(
            get_spans=lambda **_kwargs: [other_span, raw_span],
        )
    )
    backend.project_name = "default"
    backend.query_limit = 100

    spans = backend.list_for_run(run_id)

    assert len(spans) == 1
    assert spans[0].run_id == run_id
    assert spans[0].span_id == "span-1"
    assert spans[0].input == {"prompt": "hello"}
    assert spans[0].output == {"output": "world"}
    assert spans[0].trace_backend == "phoenix"


def test_build_infrastructure_requires_phoenix_configuration(monkeypatch):
    monkeypatch.setattr(settings, "phoenix_base_url", None)
    monkeypatch.setattr(settings, "phoenix_otlp_endpoint", None)

    with pytest.raises(RuntimeError, match="Phoenix-backed raw tracing is required"):
        build_infrastructure()
