from __future__ import annotations

import json
from uuid import uuid4

from agent_atlas_contracts.execution import ExecutionHandoff, RunnerRunSpec
from app.modules.execution.adapters.outbound.execution import (
    K8sLauncher,
    LocalLauncher,
    LocalProcessRunner,
    runner_run_spec_from_run_spec,
)
from app.modules.runs.application.results import PublishedRunExecutionResult
from app.modules.runs.domain.models import RunSpec, RuntimeExecutionResult
from app.modules.shared.domain.enums import AdapterKind, StepType
from app.modules.shared.domain.models import ProvenanceMetadata
from app.modules.shared.domain.traces import TraceIngestEvent


def _runner_spec() -> RunnerRunSpec:
    run_id = uuid4()
    return runner_run_spec_from_run_spec(
        RunSpec(
            run_id=run_id,
            experiment_id=uuid4(),
            project="atlas",
            dataset="ops",
            agent_id="triage-bot",
            model="gpt-5.4-mini",
            entrypoint="app.agent_plugins.basic:build_agent",
            agent_type=AdapterKind.OPENAI_AGENTS,
            input_summary="check ticket",
            prompt="Summarize the incident.",
            provenance=ProvenanceMetadata(
                framework=AdapterKind.OPENAI_AGENTS.value,
                published_agent_snapshot={
                    "manifest": {
                        "agent_id": "triage-bot",
                        "name": "Triage Bot",
                        "description": "Checks incidents",
                        "framework": AdapterKind.OPENAI_AGENTS.value,
                        "default_model": "gpt-5.4-mini",
                        "tags": [],
                    },
                    "entrypoint": "app.agent_plugins.basic:build_agent",
                },
                artifact_ref="source://triage-bot@fingerprint",
            ),
        ),
        attempt=2,
        attempt_id=uuid4(),
    )


def test_local_launcher_materializes_bootstrap_files_and_outputs(tmp_path):
    payload = _runner_spec()
    launcher = LocalLauncher(workspace_root=tmp_path)

    session = launcher.prepare(payload)

    assert session.work_dir.exists()
    assert session.payload.bootstrap.run_spec_path.startswith(str(tmp_path))
    assert session.environment["ATLAS_RUNSPEC_PATH"] == session.payload.bootstrap.run_spec_path
    assert "--artifact-manifest" in session.entrypoint_args

    materialized = RunnerRunSpec.model_validate_json(
        session.work_dir.joinpath("workspace/input/run_spec.json").read_text(encoding="utf-8")
    )
    assert materialized.run_id == payload.run_id
    assert materialized.bootstrap.run_spec_path == session.payload.bootstrap.run_spec_path

    result = PublishedRunExecutionResult(
        runtime_result=RuntimeExecutionResult(
            output="ok",
            latency_ms=12,
            token_usage=21,
            provider="mock",
        ),
        trace_events=[
            TraceIngestEvent(
                run_id=payload.run_id,
                span_id=f"span-{payload.run_id}-1",
                step_type=StepType.LLM,
                name="gpt-5.4-mini",
                input={"prompt": payload.prompt},
                output={"output": "ok", "success": True},
            )
        ],
    )

    launcher.persist_result(session, result)

    events_path = session.work_dir / "workspace/output/events.ndjson"
    terminal_result_path = session.work_dir / "workspace/output/terminal_result.json"
    artifact_manifest_path = session.work_dir / "workspace/output/artifact_manifest.json"

    event_row = json.loads(events_path.read_text(encoding="utf-8").strip())
    terminal_result = json.loads(terminal_result_path.read_text(encoding="utf-8"))
    artifact_manifest = json.loads(artifact_manifest_path.read_text(encoding="utf-8"))

    assert event_row["event_type"] == "llm.response"
    assert terminal_result["status"] == "succeeded"
    assert terminal_result["metrics"]["token_usage"] == 21
    assert artifact_manifest["artifacts"] == []


def test_local_process_runner_persists_runner_outputs_with_local_launcher(tmp_path):
    payload = _runner_spec()
    handoff = ExecutionHandoff(
        run_id=payload.run_id,
        runner_backend="local-process",
        experiment_id=payload.experiment_id,
        dataset_version_id=payload.dataset_version_id,
        attempt=payload.attempt,
        attempt_id=payload.attempt_id,
        project=payload.project,
        dataset=payload.dataset,
        agent_id=payload.agent_id,
        model=payload.model,
        entrypoint=payload.entrypoint,
        agent_type=payload.agent_type,
        input_summary=payload.input_summary,
        prompt=payload.prompt,
        tags=list(payload.tags),
        project_metadata=dict(payload.project_metadata),
        dataset_sample_id=payload.dataset_sample_id,
        framework=payload.framework,
        framework_type=payload.framework_type,
        framework_version=payload.framework_version,
        artifact_ref=payload.artifact_ref,
        image_ref=payload.image_ref,
        trace_backend=payload.trace_backend,
        published_agent_snapshot=payload.published_agent_snapshot,
    )

    class StubRuntime:
        def execute_published(self, run_id, published_payload):
            assert run_id == payload.run_id
            assert published_payload.bootstrap.run_spec_path.startswith(str(tmp_path))
            return PublishedRunExecutionResult(
                runtime_result=RuntimeExecutionResult(
                    output="runner-output",
                    latency_ms=5,
                    token_usage=8,
                    provider="mock",
                )
            )

    runner = LocalProcessRunner(
        published_runtime=StubRuntime(),
        launcher=LocalLauncher(workspace_root=tmp_path),
    )

    result = runner.execute(handoff)

    assert result.execution.runtime_result.output == "runner-output"
    materialized_root = next(tmp_path.glob(f"{payload.run_id}/*"))
    assert materialized_root.joinpath("workspace/output/terminal_result.json").exists()


def test_k8s_launcher_builds_job_manifest_from_bootstrap_contract():
    payload = _runner_spec().model_copy(
        update={
            "executor_config": {
                "backend": "k8s-job",
                "runner_image": "ghcr.io/example/atlas-runner:latest",
                "timeout_seconds": 600,
                "max_steps": 32,
                "concurrency": 1,
                "resources": {"cpu": "500m", "memory": "1Gi"},
                "tracing_backend": "phoenix",
                "artifact_path": None,
                "metadata": {"command": ["python", "-m", "atlas_runner"]},
            }
        }
    )

    request = K8sLauncher(namespace="atlas-tests").build_request(payload)

    assert request.namespace == "atlas-tests"
    assert request.image == "ghcr.io/example/atlas-runner:latest"
    assert request.env["ATLAS_RUNSPEC_PATH"] == "/workspace/input/run_spec.json"
    assert request.args[:2] == ["--run-spec", "/workspace/input/run_spec.json"]
    assert request.config_map_manifest["data"]["run_spec.json"]
    container = request.job_manifest["spec"]["template"]["spec"]["containers"][0]
    assert container["command"] == ["python", "-m", "atlas_runner"]
    assert container["volumeMounts"][0]["mountPath"] == "/workspace/input/run_spec.json"
    assert container["volumeMounts"][1]["mountPath"] == "/workspace/output"
