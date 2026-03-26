from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

from app.bootstrap.container import get_container
from app.modules.runs.domain.models import RunRecord, TrajectoryStep
from app.modules.shared.domain.enums import AdapterKind, RunStatus, StepType


def test_export_artifact_jsonl_is_training_ready(client, tmp_path):
    container = get_container()
    run_id = UUID("22222222-2222-2222-2222-222222222222")

    container.run_repository.save(
        RunRecord(
            run_id=run_id,
            input_summary="policy snapshot",
            status=RunStatus.SUCCEEDED,
            project="policy-project",
            dataset="policy-dataset",
            model="gpt-4.1-mini",
            agent_type=AdapterKind.OPENAI_AGENTS,
        )
    )

    container.trajectory_repository.append(
        TrajectoryStep(
            id="step-1",
            run_id=run_id,
            step_type=StepType.LLM,
            prompt="plan a trip",
            output="trip planned",
            model="gpt-4.1-mini",
            latency_ms=9,
            token_usage=4,
            success=True,
            temperature=0.2,
        )
    )

    container.trajectory_repository.append(
        TrajectoryStep(
            id="step-2",
            run_id=run_id,
            step_type=StepType.TOOL,
            prompt="call weather API",
            output='{"ok": true}',
            model="gpt-4.1-mini",
            latency_ms=5,
            token_usage=0,
            success=False,
            tool_name="weather",
            temperature=0.0,
        )
    )

    container.artifact_exporter.output_dir = Path(tmp_path)

    response = client.post(
        "/api/v1/artifacts/export",
        json={"run_ids": [str(run_id)], "format": "jsonl"},
    )
    assert response.status_code == 200

    payload = response.json()
    assert payload["format"] == "jsonl"
    assert payload["run_ids"] == [str(run_id)]
    assert payload["path"].endswith(".jsonl")

    artifact_path = Path(payload["path"])
    assert artifact_path.exists()
    rows = [json.loads(line) for line in artifact_path.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 2
    assert rows[0]["schema_version"] == "flight-recorder-jsonl-v1"
    assert rows[0]["split"] == "train"
    assert rows[0]["format"] == "chat"
    assert rows[0]["project"] == "policy-project"
    assert rows[0]["messages"] == [
        {
            "role": "system",
            "content": (
                "Run context: project=policy-project, "
                "dataset=policy-dataset, "
                "adapter=openai-agents-sdk"
            ),
        },
        {"role": "user", "content": "plan a trip"},
        {"role": "assistant", "content": "trip planned"},
    ]
    assert rows[0]["reward"] == 1.0
    assert rows[0]["label"]["success"] is True
    assert rows[1]["reward"] == 0.0
    assert rows[1]["label"]["success"] is False


def test_list_artifacts_returns_recent_exports(client, tmp_path):
    container = get_container()
    run_id = UUID("33333333-3333-3333-3333-333333333333")

    container.run_repository.save(
        RunRecord(
            run_id=run_id,
            input_summary="artifact listing",
            status=RunStatus.SUCCEEDED,
            project="artifact-project",
            dataset="artifact-dataset",
            model="gpt-4.1-mini",
            agent_type=AdapterKind.OPENAI_AGENTS,
        )
    )

    container.trajectory_repository.append(
        TrajectoryStep(
            id="step-artifact",
            run_id=run_id,
            step_type=StepType.LLM,
            prompt="summarize state",
            output="summary ready",
            model="gpt-4.1-mini",
            latency_ms=8,
            token_usage=5,
            success=True,
            temperature=0.0,
        )
    )

    container.artifact_exporter.output_dir = Path(tmp_path)

    response = client.post(
        "/api/v1/artifacts/export",
        json={"run_ids": [str(run_id)], "format": "jsonl"},
    )
    assert response.status_code == 200
    artifact_id = response.json()["artifact_id"]

    listing = client.get("/api/v1/artifacts")
    assert listing.status_code == 200
    payload = listing.json()
    assert any(item["artifact_id"] == artifact_id for item in payload)
