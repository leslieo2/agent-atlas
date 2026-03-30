from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from app.agent_tracing.backends.phoenix import (
    PhoenixTraceBackend,
    build_phoenix_project_url,
    build_phoenix_trace_url,
)
from app.bootstrap.wiring.infrastructure import build_infrastructure
from app.core.config import TraceBackendMode, settings
from app.modules.shared.application.contracts import RunTraceLookup


class _RunLookup:
    def __init__(self, run: RunTraceLookup) -> None:
        self.run = run

    def get(self, run_id):
        return self.run if str(self.run.run_id) == str(run_id) else None


def test_build_phoenix_urls():
    project_url = build_phoenix_project_url(
        base_url="http://phoenix.local:6006/",
        project_id="UHJvamVjdDoy",
        experiment_id="exp-123",
        run_id="run-456",
    )
    trace_url = build_phoenix_trace_url(
        base_url="http://phoenix.local:6006/",
        project_id="UHJvamVjdDoy",
        trace_id="abc123",
    )

    assert project_url == (
        "http://phoenix.local:6006/projects/UHJvamVjdDoy?" "experiment_id=exp-123&run_id=run-456"
    )
    assert trace_url == "http://phoenix.local:6006/projects/UHJvamVjdDoy/traces/abc123"


def test_build_phoenix_project_url_falls_back_to_home_without_project_id():
    project_url = build_phoenix_project_url(
        base_url="http://phoenix.local:6006/",
        project_id=None,
        experiment_id="exp-123",
    )

    assert project_url == "http://phoenix.local:6006"


def test_phoenix_trace_backend_filters_and_maps_run_spans():
    run_id = uuid4()
    run = RunTraceLookup(
        run_id=run_id,
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
    backend.run_lookup = _RunLookup(run)
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


def test_build_infrastructure_defaults_to_state_backend_without_phoenix(monkeypatch):
    monkeypatch.setattr(settings, "trace_backend", TraceBackendMode.STATE)
    monkeypatch.setattr(settings, "phoenix_base_url", None)
    monkeypatch.setattr(settings, "tracing_otlp_endpoint", None)

    infrastructure = build_infrastructure()

    assert infrastructure.trace_backend.backend_name() == "state"


def test_build_infrastructure_requires_base_url_for_phoenix_backend(monkeypatch):
    monkeypatch.setattr(settings, "trace_backend", TraceBackendMode.PHOENIX)
    monkeypatch.setattr(settings, "phoenix_base_url", None)

    with pytest.raises(RuntimeError, match="AGENT_ATLAS_PHOENIX_BASE_URL"):
        build_infrastructure()
