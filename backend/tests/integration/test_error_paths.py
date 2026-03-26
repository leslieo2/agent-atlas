from __future__ import annotations


def test_export_artifact_rejects_empty_runs(client):
    response = client.post("/api/v1/artifacts/export", json={"run_ids": [], "format": "jsonl"})
    assert response.status_code == 400
    assert response.json()["detail"] == "run_ids cannot be empty"
