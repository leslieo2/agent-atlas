from __future__ import annotations

from app.bootstrap.container import get_container
from app.modules.runs.application.results import PublishedRunExecutionResult
from app.modules.runs.domain.models import RuntimeExecutionResult


def test_end_to_end_workbench_flow(monkeypatch, client, worker_drain):
    container = get_container()
    monkeypatch.setattr(
        container.model_runtime,
        "execute_published",
        lambda *_args, **_kwargs: PublishedRunExecutionResult(
            runtime_result=RuntimeExecutionResult(
                output="mocked e2e output",
                latency_ms=1,
                token_usage=2,
                provider="mock",
                resolved_model="gpt-4.1-mini",
            )
        ),
    )

    dataset = client.post(
        "/api/v1/datasets",
        json={"name": "e2e-ds", "rows": [{"sample_id": "s-1", "input": "Hello dataset"}]},
    )
    assert dataset.status_code == 200
    assert dataset.json()["name"] == "e2e-ds"

    run = client.post(
        "/api/v1/runs",
        json={
            "project": "e2e-project",
            "dataset": "e2e-ds",
            "agent_id": "basic",
            "input_summary": "e2e smoke run",
            "prompt": "Generate safe output.",
            "tags": ["e2e"],
        },
    )
    assert run.status_code == 201
    run_id = run.json()["run_id"]

    assert worker_drain() >= 1

    run_state = client.get(f"/api/v1/runs/{run_id}")
    assert run_state.json()["status"] == "succeeded"

    trajectory = client.get(f"/api/v1/runs/{run_id}/trajectory")
    assert trajectory.status_code == 200
    trajectory_rows = trajectory.json()
    assert len(trajectory_rows) >= 1

    artifact = client.post(
        "/api/v1/artifacts/export",
        json={"run_ids": [run_id], "format": "jsonl"},
    )
    assert artifact.status_code == 200
    artifact_id = artifact.json()["artifact_id"]
    assert artifact_id

    artifact_file = client.get(f"/api/v1/artifacts/{artifact_id}")
    assert artifact_file.status_code == 200
    assert artifact_file.headers["content-type"].startswith("application/")
