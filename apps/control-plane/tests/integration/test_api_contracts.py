from __future__ import annotations


def test_openapi_exposes_rl_data_control_plane_only(client) -> None:
    response = client.get("/openapi.json")
    assert response.status_code == 200
    payload = response.json()

    paths = payload["paths"]
    assert "/api/v1/agents/published" in paths
    assert "/api/v1/agents/{agent_id}/validation-runs" in paths
    assert "/api/v1/datasets" in paths
    assert "/api/v1/datasets/{dataset_name}" in paths
    assert "/api/v1/datasets/{dataset_name}/versions" in paths
    assert "/api/v1/experiments" in paths
    assert "/api/v1/experiments/compare" in paths
    assert "/api/v1/experiments/{experiment_id}" in paths
    assert "/api/v1/experiments/{experiment_id}/start" in paths
    assert "/api/v1/experiments/{experiment_id}/cancel" in paths
    assert "/api/v1/experiments/{experiment_id}/runs" in paths
    assert "/api/v1/experiments/{experiment_id}/runs/{run_id}" in paths
    assert "/api/v1/exports" in paths
    assert "/api/v1/exports/{export_id}" in paths
    assert "/api/v1/policies" in paths
    assert "/api/v1/runs/{run_id}" in paths

    assert "/api/v1/runs" not in paths
    assert "/api/v1/eval-jobs" not in paths
    assert "/api/v1/traces/ingest" not in paths
    assert "/api/v1/artifacts" not in paths
    assert "/api/v1/artifacts/export" not in paths

    schemas = payload["components"]["schemas"]
    assert "DatasetResponse" in schemas
    assert "DatasetVersionResponse" in schemas
    assert "ExperimentResponse" in schemas
    assert "ExperimentCompareResponse" in schemas
    assert "ExperimentRunResponse" in schemas
    assert "ApprovalPolicyResponse" in schemas
    assert "ExportCreateRequest" in schemas
    assert "ExportMetadataResponse" in schemas
    assert "RunResponse" in schemas
    assert "ArtifactMetadataResponse" not in schemas
