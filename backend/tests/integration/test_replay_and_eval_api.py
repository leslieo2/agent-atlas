from __future__ import annotations

import time
from uuid import uuid4

from app.bootstrap.container import get_container
from app.modules.runs.domain.models import TrajectoryStep
from app.modules.shared.domain.enums import StepType


def test_replay_api_creates_and_fetches_replay(client):
    container = get_container()
    run_id = uuid4()
    container.trajectory_repository.append(
        TrajectoryStep(
            id="step-1",
            run_id=run_id,
            step_type=StepType.LLM,
            prompt="Explain the plan.",
            output="baseline-output",
            model="gpt-4.1-mini",
            temperature=0.0,
            latency_ms=11,
            token_usage=4,
            success=True,
        )
    )

    response = client.post(
        "/api/v1/replays",
        json={
            "run_id": str(run_id),
            "step_id": "step-1",
            "edited_prompt": "Explain the plan with more detail.",
            "model": "gpt-4.1-mini",
        },
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["run_id"] == str(run_id)
    assert payload["step_id"] == "step-1"
    assert payload["updated_prompt"] == "Explain the plan with more detail."
    assert payload["baseline_output"] == "baseline-output"
    assert "Replay output for step step-1" in payload["replay_output"]

    replay_id = payload["replay_id"]
    fetched = client.get(f"/api/v1/replays/{replay_id}")
    assert fetched.status_code == 200
    fetched_payload = fetched.json()
    assert fetched_payload["replay_id"] == replay_id
    assert fetched_payload["step_id"] == "step-1"
    assert fetched_payload["diff"]


def test_eval_job_api_completes_and_returns_results(client):
    run_id = str(uuid4())

    response = client.post(
        "/api/v1/eval-jobs",
        json={"run_ids": [run_id], "dataset": "crm-v2"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["run_ids"] == [run_id]
    assert payload["dataset"] == "crm-v2"
    assert payload["status"] in {"queued", "running", "done"}

    deadline = time.time() + 3.0
    while time.time() < deadline:
        current = client.get(f"/api/v1/eval-jobs/{payload['job_id']}")
        assert current.status_code == 200
        current_payload = current.json()
        if current_payload["status"] == "done":
            break
        time.sleep(0.05)
    else:
        raise AssertionError("eval job did not complete in time")

    assert current_payload["job_id"] == payload["job_id"]
    assert current_payload["run_ids"] == [run_id]
    assert current_payload["dataset"] == "crm-v2"
    assert len(current_payload["results"]) == 1
    result = current_payload["results"][0]
    assert result["run_id"] == run_id
    assert result["sample_id"].startswith("sample-1-")
    assert result["status"] in {"pass", "fail"}
    assert 0.45 <= result["score"] <= 0.98
