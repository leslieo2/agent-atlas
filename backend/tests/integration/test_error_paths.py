from __future__ import annotations


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
