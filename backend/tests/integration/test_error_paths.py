from __future__ import annotations

from uuid import uuid4

from app.bootstrap.container import get_container
from app.core.errors import ModelNotFoundError
from app.modules.runs.domain.models import RunRecord, TrajectoryStep
from app.modules.shared.domain.enums import AdapterKind, RunStatus, StepType


def test_empty_eval_job_request_is_invalid(client):
    response = client.post("/api/v1/eval-jobs", json={"run_ids": [], "dataset": "crm-v2"})
    assert response.status_code == 400
    assert response.json()["detail"] == "run_ids cannot be empty"


def test_replay_missing_step_returns_404(client):
    payload = {
        "run_id": "a6f3f2a1-1111-4f8d-9999-111111111111",
        "step_id": "non-existent-step",
        "edited_prompt": "patched",
        "model": "gpt-4.1-mini",
    }
    response = client.post("/api/v1/replays", json=payload)
    assert response.status_code == 404
    assert response.json()["detail"] == "step 'non-existent-step' not found"


def test_export_artifact_rejects_empty_runs(client):
    response = client.post("/api/v1/artifacts/export", json={"run_ids": [], "format": "jsonl"})
    assert response.status_code == 400
    assert response.json()["detail"] == "run_ids cannot be empty"


def test_replay_id_invalid_format_returns_400(client):
    response = client.get("/api/v1/replays/not-a-uuid")
    assert response.status_code == 400
    assert response.json()["detail"] == "invalid replay_id"


def test_replay_invalid_model_returns_structured_400(client, monkeypatch):
    container = get_container()
    run_id = uuid4()
    container.run_repository.save(
        RunRecord(
            run_id=run_id,
            input_summary="replay invalid model",
            status=RunStatus.SUCCEEDED,
            project="workbench",
            dataset="crm-v2",
            model="gpt-4.1-mini",
            agent_type=AdapterKind.OPENAI_AGENTS,
            tags=["replay"],
        )
    )
    container.trajectory_repository.append(
        TrajectoryStep(
            id="step-invalid-model",
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

    def raise_model_not_found(*_args, **_kwargs):
        raise ModelNotFoundError("planner-v1")

    monkeypatch.setattr(container.runner_registry.default_runner, "execute", raise_model_not_found)

    response = client.post(
        "/api/v1/replays",
        json={
            "run_id": str(run_id),
            "step_id": "step-invalid-model",
            "edited_prompt": "Explain the plan with more detail.",
            "model": "planner-v1",
        },
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": {
            "code": "model_not_found",
            "message": "model 'planner-v1' not found",
            "model": "planner-v1",
        }
    }
