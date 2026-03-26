from __future__ import annotations

from uuid import uuid4

from app.bootstrap.container import get_container
from app.modules.runs.domain.models import RunRecord, RuntimeExecutionResult, TrajectoryStep
from app.modules.shared.domain.enums import AdapterKind, RunStatus, StepType


def test_replay_api_creates_and_fetches_replay(client, monkeypatch):
    container = get_container()
    run_id = uuid4()
    container.run_repository.save(
        RunRecord(
            run_id=run_id,
            input_summary="replay api seed",
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
    monkeypatch.setattr(
        container.runner_registry.default_runner,
        "execute",
        lambda *_args, **_kwargs: RuntimeExecutionResult(
            output="live api replay output",
            latency_ms=12,
            token_usage=8,
            provider="stub",
        ),
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
    assert payload["replay_output"] == "live api replay output"

    replay_id = payload["replay_id"]
    fetched = client.get(f"/api/v1/replays/{replay_id}")
    assert fetched.status_code == 200
    fetched_payload = fetched.json()
    assert fetched_payload["replay_id"] == replay_id
    assert fetched_payload["step_id"] == "step-1"
    assert fetched_payload["diff"]


def test_eval_job_api_completes_and_returns_results(client, worker_drain):
    run_id = str(uuid4())

    response = client.post(
        "/api/v1/eval-jobs",
        json={"run_ids": [run_id], "dataset": "crm-v2"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["run_ids"] == [run_id]
    assert payload["dataset"] == "crm-v2"
    assert payload["status"] == "queued"

    assert worker_drain() >= 1

    current = client.get(f"/api/v1/eval-jobs/{payload['job_id']}")
    assert current.status_code == 200
    current_payload = current.json()
    assert current_payload["status"] == "done"

    assert current_payload["job_id"] == payload["job_id"]
    assert current_payload["run_ids"] == [run_id]
    assert current_payload["dataset"] == "crm-v2"
    assert len(current_payload["results"]) == 1
    result = current_payload["results"][0]
    assert result["run_id"] == run_id
    assert result["sample_id"].startswith("sample-1-")
    assert result["status"] in {"pass", "fail"}
    assert 0.45 <= result["score"] <= 0.98


def test_eval_job_stays_queued_until_worker_runs(client):
    run_id = str(uuid4())

    response = client.post(
        "/api/v1/eval-jobs",
        json={"run_ids": [run_id], "dataset": "crm-v2"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "queued"

    current = client.get(f"/api/v1/eval-jobs/{payload['job_id']}")
    assert current.status_code == 200
    assert current.json()["status"] == "queued"


def test_candidate_run_provenance_persists_through_runs_api(client):
    baseline_response = client.post(
        "/api/v1/runs",
        json={
            "project": "replay-lab",
            "dataset": "crm-v2",
            "agent_id": "basic",
            "input_summary": "baseline run",
            "prompt": "Reply with exactly one token: alpha",
            "tags": ["baseline"],
        },
    )
    assert baseline_response.status_code == 201
    baseline_payload = baseline_response.json()

    candidate_response = client.post(
        "/api/v1/runs",
        json={
            "project": "replay-lab",
            "dataset": "crm-v2",
            "agent_id": "basic",
            "input_summary": "candidate run",
            "prompt": "Reply with exactly one token: beta",
            "tags": ["candidate", "replay"],
            "project_metadata": {
                "candidate": {
                    "kind": "replay",
                    "sourceRunId": baseline_payload["run_id"],
                    "sourceStepId": "step-1",
                    "replayId": "replay-123",
                    "diff": "patched output",
                },
                "sourceRun": {
                    "project": "replay-lab",
                    "dataset": "crm-v2",
                    "model": "gpt-4.1-mini",
                    "agentType": "openai-agents-sdk",
                    "agentId": "basic",
                },
            },
        },
    )
    assert candidate_response.status_code == 201
    candidate_payload = candidate_response.json()

    assert candidate_payload["project_metadata"]["candidate"] == {
        "kind": "replay",
        "sourceRunId": baseline_payload["run_id"],
        "sourceStepId": "step-1",
        "replayId": "replay-123",
        "diff": "patched output",
    }
    assert candidate_payload["project_metadata"]["sourceRun"] == {
        "project": "replay-lab",
        "dataset": "crm-v2",
        "model": "gpt-4.1-mini",
        "agentType": "openai-agents-sdk",
        "agentId": "basic",
    }
    assert candidate_payload["project_metadata"]["prompt"] == "Reply with exactly one token: beta"
    assert candidate_payload["project_metadata"]["agent_snapshot"] == {
        "entrypoint": "app.registered_agents.basic:build_agent",
        "framework": "openai-agents-sdk",
        "default_model": "gpt-4.1-mini",
        "registry_tags": ["example", "smoke"],
    }

    fetched_candidate = client.get(f"/api/v1/runs/{candidate_payload['run_id']}")
    assert fetched_candidate.status_code == 200
    assert fetched_candidate.json()["project_metadata"] == candidate_payload["project_metadata"]


def test_eval_job_api_returns_results_for_multiple_run_ids(client, worker_drain):
    baseline_run_id = str(uuid4())
    candidate_run_id = str(uuid4())

    eval_response = client.post(
        "/api/v1/eval-jobs",
        json={
            "run_ids": [baseline_run_id, candidate_run_id],
            "dataset": "crm-v2",
            "evaluators": ["rule"],
        },
    )
    assert eval_response.status_code == 200
    eval_payload = eval_response.json()
    assert eval_payload["run_ids"] == [baseline_run_id, candidate_run_id]

    assert worker_drain() >= 1

    completed_job = client.get(f"/api/v1/eval-jobs/{eval_payload['job_id']}")
    assert completed_job.status_code == 200
    completed_payload = completed_job.json()
    assert completed_payload["status"] == "done"
    assert len(completed_payload["results"]) == 2
    assert {result["run_id"] for result in completed_payload["results"]} == {
        baseline_run_id,
        candidate_run_id,
    }
