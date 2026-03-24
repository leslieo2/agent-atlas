from __future__ import annotations

import time
from uuid import uuid4

from app.models.schemas import RunStatus


def test_runs_api_create_list_and_trajectory_filters(monkeypatch, client):
    monkeypatch.setattr(
        "app.services.orchestrator.execute_with_fallback",
        lambda *_args, **_kwargs: {
            "output": "mocked integration output",
            "latency_ms": 1,
            "token_usage": 1,
            "provider": "mock",
        },
    )

    response = client.post(
        "/api/v1/runs",
        json={
            "project": "integration",
            "dataset": "crm-v2",
            "model": "gpt-4.1-mini",
            "agent_type": "openai-agents-sdk",
            "input_summary": "integration smoke",
            "prompt": "Say hello.",
            "tags": ["integration"],
        },
    )
    assert response.status_code == 201

    run = response.json()
    run_id = run["run_id"]
    assert run["project"] == "integration"
    assert run["status"] in {RunStatus.QUEUED.value, RunStatus.RUNNING.value}

    deadline = time.time() + 3.0
    while time.time() < deadline:
        current = client.get(f"/api/v1/runs/{run_id}")
        assert current.status_code == 200
        data = current.json()
        if data["status"] == RunStatus.SUCCEEDED.value:
            break
        time.sleep(0.05)
    else:
        raise AssertionError("run did not complete in integration test timeout")

    trajectory = client.get(f"/api/v1/runs/{run_id}/trajectory").json()
    assert isinstance(trajectory, list)
    assert len(trajectory) >= 4

    filtered = client.get("/api/v1/runs", params={"project": "integration"}).json()
    assert any(item["run_id"] == run_id for item in filtered)


def test_trace_ingest_and_normalize_endpoints(client):
    run_id = str(uuid4())

    normalize_payload = {
        "run_id": run_id,
        "span_id": "span-normalize",
        "parent_span_id": None,
        "step_type": "tool",
        "name": "normalize-step",
        "input": {"task": "normalize"},
        "output": {"ok": True},
        "tool_name": "mcp",
        "latency_ms": 7,
        "token_usage": 3,
        "image_digest": "sha256:normalize",
        "prompt_version": "v1",
    }

    normalized = client.post("/api/v1/traces/normalize", json=normalize_payload)
    assert normalized.status_code == 200
    normalized_payload = normalized.json()
    assert normalized_payload["run_id"] == run_id
    assert normalized_payload["step_type"] == "tool"

    ingested = client.post("/api/v1/traces/ingest", json=normalize_payload)
    assert ingested.status_code == 201
    assert ingested.json()["status"] == "ok"
    assert ingested.json()["span_id"] == "span-normalize"

    traces = client.get(f"/api/v1/runs/{run_id}/traces").json()
    assert len(traces) == 1
    assert traces[0]["span_id"] == "span-normalize"


def test_adapters_list_available_adapters(client):
    adapters = client.get("/api/v1/adapters").json()
    assert {adapter["kind"] for adapter in adapters} == {
        "openai-agents-sdk",
        "langchain",
        "mcp",
    }
