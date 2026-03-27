from __future__ import annotations

import builtins
import json
from pathlib import Path
from uuid import UUID

from app.bootstrap.container import get_container
from app.modules.runs.domain.models import TrajectoryStep
from app.modules.shared.domain.enums import StepType


def test_export_artifact_parquet_falls_back_when_optional_deps_missing(
    monkeypatch,
    client,
    tmp_path,
):
    container = get_container()
    run_id = UUID("11111111-1111-1111-1111-111111111111")
    container.infrastructure.trajectory_repository.append(
        TrajectoryStep(
            id="step-1",
            run_id=run_id,
            step_type=StepType.LLM,
            prompt="plan a trip",
            output="trip planned",
            model="gpt-5.4-mini",
            latency_ms=9,
            token_usage=4,
            success=True,
        )
    )

    real_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name in {"pandas", "pyarrow", "pyarrow.parquet"}:
            raise ImportError(f"missing optional dependency: {name}")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    container.artifacts.artifact_exporter.output_dir = Path(tmp_path)

    response = client.post(
        "/api/v1/artifacts/export",
        json={"run_ids": [str(run_id)], "format": "parquet"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["format"] == "parquet"
    assert payload["run_ids"] == [str(run_id)]
    assert payload["path"].endswith(".parquet")

    artifact_path = Path(payload["path"])
    assert artifact_path.exists()

    fallback = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert fallback["format"] == "parquet"
    assert fallback["run_ids"] == [str(run_id)]
    assert "parquet output unavailable" in fallback["message"]
