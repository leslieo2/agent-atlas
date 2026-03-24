from __future__ import annotations

from uuid import uuid4


def test_end_to_end_error_flow_replay_step_not_found(client):
    response = client.post(
        "/api/v1/replays",
        json={"run_id": "a6f3f2a1-1111-4f8d-9999-111111111111", "step_id": "no-such-step"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "step 'no-such-step' not found"


def test_end_to_end_error_flow_artifact_not_found(client):
    artifact = client.get(f"/api/v1/artifacts/{uuid4()}")
    assert artifact.status_code == 404
    assert artifact.json()["detail"] == "artifact not found"


def test_end_to_end_error_flow_invalid_artifact_id(client):
    artifact = client.get("/api/v1/artifacts/not-a-uuid")
    assert artifact.status_code == 400
    assert artifact.json()["detail"] == "invalid artifact_id"
