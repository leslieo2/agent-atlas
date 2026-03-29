from __future__ import annotations


def test_openapi_exposes_rl_data_control_plane_only(client) -> None:
    response = client.get("/openapi.json")
    assert response.status_code == 200
    payload = response.json()

    paths = payload["paths"]
    assert "/api/v1/agents" in paths
    assert "/api/v1/datasets" in paths
    assert "/api/v1/datasets/{dataset_name}" in paths
    assert "/api/v1/eval-jobs" in paths
    assert "/api/v1/eval-jobs/compare" in paths
    assert "/api/v1/eval-jobs/{eval_job_id}/samples/{dataset_sample_id}" in paths
    assert "/api/v1/exports" in paths
    assert "/api/v1/exports/{export_id}" in paths

    assert "/api/v1/runs" not in paths
    assert "/api/v1/runs/{run_id}" not in paths
    assert "/api/v1/traces/ingest" not in paths
    assert "/api/v1/artifacts" not in paths
    assert "/api/v1/artifacts/export" not in paths

    schemas = payload["components"]["schemas"]
    assert "DatasetResponse" in schemas
    assert "EvalCompareResponse" in schemas
    assert "EvalSampleDetailResponse" in schemas
    assert "ExportCreateRequest" in schemas
    assert "ExportMetadataResponse" in schemas
    assert "RunResponse" not in schemas
    assert "ArtifactMetadataResponse" not in schemas
