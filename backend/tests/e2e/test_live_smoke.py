from __future__ import annotations

import os
from uuid import uuid4

import pytest
from app.core.config import settings
from app.infrastructure.adapters.model_runtime import model_runtime_service
from pydantic import SecretStr


def _require_live_openai_env() -> str:
    if os.getenv("AFLIGHT_LIVE_TESTS") != "1":
        pytest.skip("set AFLIGHT_LIVE_TESTS=1 to enable real OpenAI smoke tests")

    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("AFLIGHT_OPENAI_API_KEY")
    if not api_key:
        pytest.skip("set OPENAI_API_KEY or AFLIGHT_OPENAI_API_KEY for live smoke tests")

    return api_key


@pytest.fixture
def live_openai_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    api_key = _require_live_openai_env()
    monkeypatch.setattr(settings, "runtime_mode", "live")
    monkeypatch.setattr(settings, "runner_mode", "local")
    monkeypatch.setattr(model_runtime_service, "api_key", SecretStr(api_key))
    monkeypatch.setattr(model_runtime_service, "runtime_mode", "live")


def test_live_openai_run_eval_export_smoke(client, worker_drain, live_openai_runtime) -> None:
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
            "model": "gpt-4.1-mini",
            "agent_type": "openai-agents-sdk",
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

    eval_job = client.post(
        "/api/v1/eval-jobs",
        json={"run_ids": [run_id], "dataset": dataset_name, "evaluators": ["rule"]},
    )
    assert eval_job.status_code == 200
    job_id = eval_job.json()["job_id"]

    assert worker_drain(limit=2) >= 1

    job = client.get(f"/api/v1/eval-jobs/{job_id}")
    assert job.status_code == 200
    job_payload = job.json()
    assert job_payload["status"] == "done"
    assert len(job_payload["results"]) == 1
    assert job_payload["results"][0]["run_id"] == run_id

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
