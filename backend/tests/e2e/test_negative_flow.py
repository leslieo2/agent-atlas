from __future__ import annotations

from uuid import uuid4

from app.bootstrap.container import get_container
from app.modules.runs.domain.models import RunRecord
from app.modules.shared.domain.enums import AdapterKind, RunStatus


def test_end_to_end_error_flow_replay_step_not_found(client):
    run_id = uuid4()
    get_container().run_repository.save(
        RunRecord(
            run_id=run_id,
            input_summary="negative replay seed",
            status=RunStatus.SUCCEEDED,
            project="workbench",
            dataset="crm-v2",
            model="gpt-4.1-mini",
            agent_type=AdapterKind.OPENAI_AGENTS,
            tags=["replay"],
        )
    )
    response = client.post(
        "/api/v1/replays",
        json={"run_id": str(run_id), "step_id": "no-such-step"},
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
