from __future__ import annotations

import os
from uuid import uuid4

import pytest
from app.bootstrap.container import get_container
from app.core.config import settings
from pydantic import SecretStr


def _require_live_openai_env() -> str:
    if os.getenv("AGENT_ATLAS_LIVE_TESTS") != "1":
        pytest.skip("set AGENT_ATLAS_LIVE_TESTS=1 to enable real OpenAI smoke tests")

    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("AGENT_ATLAS_OPENAI_API_KEY")
    if not api_key:
        pytest.skip("set OPENAI_API_KEY or AGENT_ATLAS_OPENAI_API_KEY for live smoke tests")

    return api_key


@pytest.fixture
def live_openai_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    api_key = _require_live_openai_env()
    container = get_container()
    monkeypatch.setattr(settings, "runtime_mode", "live")
    monkeypatch.setattr(container.model_runtime, "api_key", SecretStr(api_key))
    monkeypatch.setattr(container.model_runtime, "runtime_mode", "live")


def test_live_openai_run_export_smoke(client, worker_drain, live_openai_runtime) -> None:
    scope = uuid4().hex[:8]
    dataset_name = f"live-smoke-{scope}"

    dataset = client.post(
        "/api/v1/datasets",
        json={
            "name": dataset_name,
            "rows": [
                {
                    "sample_id": f"sample-{scope}",
                    "input": "Reply with exactly one token: alpha",
                },
            ],
        },
    )
    assert dataset.status_code == 200

    run = client.post(
        "/api/v1/runs",
        json={
            "project": f"live-smoke-{scope}",
            "dataset": dataset_name,
            "agent_id": "basic",
            "input_summary": "reply with the token alpha",
            "prompt": "Reply with exactly one token: alpha",
            "tags": ["live", "smoke"],
        },
    )
    assert run.status_code == 201
    run_id = run.json()["run_id"]

    assert worker_drain(limit=2) >= 1

    run_state = client.get(f"/api/v1/runs/{run_id}")
    assert run_state.status_code == 200
    run_payload = run_state.json()
    assert run_payload["status"] == "succeeded"
    assert run_payload["latency_ms"] > 0
    assert run_payload["token_cost"] > 0

    trajectory = client.get(f"/api/v1/runs/{run_id}/trajectory")
    assert trajectory.status_code == 200
    trajectory_rows = trajectory.json()
    assert len(trajectory_rows) >= 1
    assert all(step["step_type"] == "llm" for step in trajectory_rows)

    artifact = client.post(
        "/api/v1/artifacts/export",
        json={"run_ids": [run_id], "format": "jsonl"},
    )
    assert artifact.status_code == 200
    artifact_payload = artifact.json()
    assert artifact_payload["artifact_id"]

    artifact_file = client.get(f"/api/v1/artifacts/{artifact_payload['artifact_id']}")
    assert artifact_file.status_code == 200
    assert artifact_file.headers["content-type"].startswith("application/")
