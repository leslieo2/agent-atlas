from __future__ import annotations

import time


def test_end_to_end_workbench_flow(monkeypatch, client):
    monkeypatch.setattr(
        "app.services.orchestrator.execute_with_fallback",
        lambda *_args, **_kwargs: {
            "output": "mocked e2e output",
            "latency_ms": 1,
            "token_usage": 2,
            "provider": "mock",
        },
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
            "model": "gpt-4.1-mini",
            "agent_type": "openai-agents-sdk",
            "input_summary": "e2e smoke run",
            "prompt": "Generate safe output.",
            "tags": ["e2e"],
        },
    )
    assert run.status_code == 201
    run_id = run.json()["run_id"]

    deadline = time.time() + 3.0
    while time.time() < deadline:
        run_state = client.get(f"/api/v1/runs/{run_id}")
        status = run_state.json()["status"]
        if status == "succeeded":
            break
        time.sleep(0.05)
    else:
        raise AssertionError("run did not finish in e2e timeout")

    trajectory = client.get(f"/api/v1/runs/{run_id}/trajectory")
    assert trajectory.status_code == 200
    trajectory_rows = trajectory.json()
    assert len(trajectory_rows) >= 4

    replay = client.post(
        "/api/v1/replays",
        json={
            "run_id": run_id,
            "step_id": trajectory_rows[0]["id"],
            "edited_prompt": "patched prompt",
            "model": "gpt-4.1-mini",
        },
    )
    assert replay.status_code == 201
    replay_payload = replay.json()
    assert replay_payload["replay_id"]
    assert replay_payload["run_id"] == run_id
    assert replay_payload["step_id"] == trajectory_rows[0]["id"]

    eval_job = client.post(
        "/api/v1/eval-jobs",
        json={"run_ids": [run_id], "dataset": "e2e-ds", "evaluators": ["rule", "judge"]},
    )
    assert eval_job.status_code == 200
    job_id = eval_job.json()["job_id"]

    deadline = time.time() + 2.5
    while time.time() < deadline:
        job = client.get(f"/api/v1/eval-jobs/{job_id}")
        if job.json()["status"] == "done":
            break
        time.sleep(0.05)
    else:
        raise AssertionError("eval job did not complete in e2e timeout")

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
