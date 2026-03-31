from __future__ import annotations

import json
import sys
from uuid import uuid4

import pytest
from agent_atlas_contracts.execution import ExecutionHandoff, RunnerBootstrapPaths, RunnerRunSpec
from app.core.errors import AgentFrameworkMismatchError, AppError
from app.execution.adapters import (
    K8sLauncher,
    LocalLauncher,
    LocalProcessRunner,
    runner_run_spec_from_run_spec,
)
from app.execution.application.results import (
    PublishedRunExecutionResult,
    RuntimeExecutionResult,
)
from app.execution.contracts import ExecutionRunSpec
from app.modules.shared.domain.enums import AdapterKind, StepType
from app.modules.shared.domain.models import ProvenanceMetadata
from app.modules.shared.domain.traces import TraceIngestEvent


def _runner_spec() -> RunnerRunSpec:
    run_id = uuid4()
    return runner_run_spec_from_run_spec(
        ExecutionRunSpec(
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
    runtime_result_path = session.work_dir / "workspace/output/runtime_result.json"
    terminal_result_path = session.work_dir / "workspace/output/terminal_result.json"
    artifact_manifest_path = session.work_dir / "workspace/output/artifact_manifest.json"

    event_row = json.loads(events_path.read_text(encoding="utf-8").strip())
    runtime_result = json.loads(runtime_result_path.read_text(encoding="utf-8"))
    terminal_result = json.loads(terminal_result_path.read_text(encoding="utf-8"))
    artifact_manifest = json.loads(artifact_manifest_path.read_text(encoding="utf-8"))

    assert event_row["event_type"] == "llm.response"
    assert runtime_result["provider"] == "mock"
    assert terminal_result["status"] == "succeeded"
    assert terminal_result["metrics"]["token_usage"] == 21
    assert artifact_manifest["artifacts"] == []


def test_local_process_runner_persists_runner_outputs_with_local_launcher(tmp_path):
    class StubPublishedRuntime:
        def execute_published(
            self,
            run_id,
            payload: RunnerRunSpec,
        ) -> PublishedRunExecutionResult:
            return PublishedRunExecutionResult(
                runtime_result=RuntimeExecutionResult(
                    output=f"in-process:{run_id}",
                    latency_ms=9,
                    token_usage=4,
                    provider="stub",
                ),
                trace_events=[
                    TraceIngestEvent(
                        run_id=payload.run_id,
                        span_id=f"span-{payload.run_id}-1",
                        step_type=StepType.LLM,
                        name=payload.model,
                        input={"prompt": payload.prompt},
                        output={"output": "ok", "success": True},
                    )
                ],
            )

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
        prompt=payload.prompt,
        tags=list(payload.tags),
        project_metadata=dict(payload.project_metadata),
        dataset_sample_id=payload.dataset_sample_id,
        framework=payload.framework,
        artifact_ref=payload.artifact_ref,
        image_ref=payload.image_ref,
        trace_backend=payload.trace_backend,
        published_agent_snapshot=payload.published_agent_snapshot,
        executor_config={**dict(payload.executor_config), "runner_mode": "in-process"},
    )

    runner = LocalProcessRunner(
        launcher=LocalLauncher(workspace_root=tmp_path),
        published_runtime=StubPublishedRuntime(),
    )

    result = runner.execute(handoff)

    assert result.execution.runtime_result.output
    assert result.execution.runtime_result.provider == "stub"
    materialized_root = next(tmp_path.glob(f"{payload.run_id}/*"))
    assert materialized_root.joinpath("workspace/output/runtime_result.json").exists()
    assert materialized_root.joinpath("workspace/output/terminal_result.json").exists()


def test_local_process_runner_preserves_runtime_metadata_from_subprocess(tmp_path):
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
        prompt=payload.prompt,
        tags=list(payload.tags),
        project_metadata=dict(payload.project_metadata),
        executor_config=dict(payload.executor_config),
        dataset_sample_id=payload.dataset_sample_id,
        framework=payload.framework,
        artifact_ref=payload.artifact_ref,
        image_ref=payload.image_ref,
        trace_backend=payload.trace_backend,
        published_agent_snapshot=payload.published_agent_snapshot,
    )
    script = """
import argparse
import json
from pathlib import Path

from agent_atlas_contracts.execution import ArtifactManifest, TerminalMetrics, TerminalResult
from agent_atlas_contracts.runtime import RuntimeExecutionResult, producer_for_runtime

parser = argparse.ArgumentParser()
parser.add_argument("--run-spec", required=True)
parser.add_argument("--events", required=True)
parser.add_argument("--runtime-result", required=True)
parser.add_argument("--terminal-result", required=True)
parser.add_argument("--artifact-manifest", required=True)
parser.add_argument("--artifact-dir", required=True)
args = parser.parse_args()

payload = json.loads(Path(args.run_spec).read_text())
run_id = payload["run_id"]
experiment_id = payload.get("experiment_id")
attempt = payload["attempt"]
attempt_id = payload.get("attempt_id")
framework = payload.get("framework")

runtime_result = RuntimeExecutionResult(
    output="subprocess ok",
    latency_ms=23,
    token_usage=34,
    provider="langchain",
    execution_backend="langgraph",
    container_image="ghcr.io/example/runner:123",
    resolved_model="gpt-5.4-mini-resolved",
)
Path(args.runtime_result).write_text(runtime_result.model_dump_json(indent=2), encoding="utf-8")
terminal_result = TerminalResult(
    run_id=run_id,
    experiment_id=experiment_id,
    attempt=attempt,
    attempt_id=attempt_id,
    status="succeeded",
    output="subprocess ok",
    producer=producer_for_runtime(runtime="langchain", framework=framework),
    metrics=TerminalMetrics(latency_ms=23, token_usage=34),
)
Path(args.terminal_result).write_text(terminal_result.model_dump_json(indent=2), encoding="utf-8")
manifest = ArtifactManifest(
    run_id=run_id,
    experiment_id=experiment_id,
    attempt=attempt,
    attempt_id=attempt_id,
    producer=producer_for_runtime(runtime="langchain", framework=framework),
    artifacts=[],
)
Path(args.artifact_manifest).write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
Path(args.events).write_text("", encoding="utf-8")
"""
    runner = LocalProcessRunner(
        launcher=LocalLauncher(workspace_root=tmp_path),
        command=[sys.executable, "-c", script],
    )

    result = runner.execute(handoff)

    assert result.execution.runtime_result.execution_backend == "langgraph"
    assert result.execution.runtime_result.container_image == "ghcr.io/example/runner:123"
    assert result.execution.runtime_result.resolved_model == "gpt-5.4-mini-resolved"


def test_local_process_runner_rehydrates_serialized_app_error(tmp_path):
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
        prompt=payload.prompt,
        tags=list(payload.tags),
        project_metadata=dict(payload.project_metadata),
        executor_config=dict(payload.executor_config),
        dataset_sample_id=payload.dataset_sample_id,
        framework=payload.framework,
        artifact_ref=payload.artifact_ref,
        image_ref=payload.image_ref,
        trace_backend=payload.trace_backend,
        published_agent_snapshot=payload.published_agent_snapshot,
    )
    script = """
import argparse
import json
import sys
from pathlib import Path

from agent_atlas_contracts.execution import ArtifactManifest, TerminalMetrics, TerminalResult
from agent_atlas_contracts.runtime import producer_for_runtime

parser = argparse.ArgumentParser()
parser.add_argument("--run-spec", required=True)
parser.add_argument("--events", required=True)
parser.add_argument("--runtime-result", required=True)
parser.add_argument("--terminal-result", required=True)
parser.add_argument("--artifact-manifest", required=True)
parser.add_argument("--artifact-dir", required=True)
args = parser.parse_args()

payload = json.loads(Path(args.run_spec).read_text())
run_id = payload["run_id"]
experiment_id = payload.get("experiment_id")
attempt = payload["attempt"]
attempt_id = payload.get("attempt_id")
framework = payload.get("framework")

terminal_result = TerminalResult(
    run_id=run_id,
    experiment_id=experiment_id,
    attempt=attempt,
    attempt_id=attempt_id,
    status="failed",
    reason_code="agent_framework_mismatch",
    reason_message="framework mismatch",
    reason_context={
        "agent_id": "triage-bot",
        "expected_framework": "openai-agents-sdk",
        "actual_framework": "langgraph",
    },
    output="framework mismatch",
    producer=producer_for_runtime(runtime="local-subprocess", framework=framework),
    metrics=TerminalMetrics(),
)
Path(args.terminal_result).write_text(terminal_result.model_dump_json(indent=2), encoding="utf-8")
manifest = ArtifactManifest(
    run_id=run_id,
    experiment_id=experiment_id,
    attempt=attempt,
    attempt_id=attempt_id,
    producer=producer_for_runtime(runtime="local-subprocess", framework=framework),
    artifacts=[],
)
Path(args.artifact_manifest).write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
Path(args.events).write_text("", encoding="utf-8")
sys.exit(1)
"""
    runner = LocalProcessRunner(
        launcher=LocalLauncher(workspace_root=tmp_path),
        command=[sys.executable, "-c", script],
    )

    with pytest.raises(AgentFrameworkMismatchError) as exc_info:
        runner.execute(handoff)

    assert exc_info.value.context["agent_id"] == "triage-bot"
    assert exc_info.value.context["expected_framework"] == "openai-agents-sdk"
    assert exc_info.value.context["actual_framework"] == "langgraph"


def test_local_process_runner_preserves_unknown_app_error_codes(tmp_path):
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
        prompt=payload.prompt,
        tags=list(payload.tags),
        project_metadata=dict(payload.project_metadata),
        executor_config=dict(payload.executor_config),
        dataset_sample_id=payload.dataset_sample_id,
        framework=payload.framework,
        artifact_ref=payload.artifact_ref,
        image_ref=payload.image_ref,
        trace_backend=payload.trace_backend,
        published_agent_snapshot=payload.published_agent_snapshot,
    )
    script = """
import argparse
import json
import sys
from pathlib import Path

from agent_atlas_contracts.execution import ArtifactManifest, TerminalMetrics, TerminalResult
from agent_atlas_contracts.runtime import producer_for_runtime

parser = argparse.ArgumentParser()
parser.add_argument("--run-spec", required=True)
parser.add_argument("--events", required=True)
parser.add_argument("--runtime-result", required=True)
parser.add_argument("--terminal-result", required=True)
parser.add_argument("--artifact-manifest", required=True)
parser.add_argument("--artifact-dir", required=True)
args = parser.parse_args()

payload = json.loads(Path(args.run_spec).read_text())
run_id = payload["run_id"]
experiment_id = payload.get("experiment_id")
attempt = payload["attempt"]
attempt_id = payload.get("attempt_id")
framework = payload.get("framework")

terminal_result = TerminalResult(
    run_id=run_id,
    experiment_id=experiment_id,
    attempt=attempt,
    attempt_id=attempt_id,
    status="failed",
    reason_code="tool_backend_error",
    reason_message="tool backend unavailable",
    reason_context={"order_id": "ORD-ERR-100"},
    output="tool backend unavailable",
    producer=producer_for_runtime(runtime="local-subprocess", framework=framework),
    metrics=TerminalMetrics(),
)
Path(args.terminal_result).write_text(terminal_result.model_dump_json(indent=2), encoding="utf-8")
manifest = ArtifactManifest(
    run_id=run_id,
    experiment_id=experiment_id,
    attempt=attempt,
    attempt_id=attempt_id,
    producer=producer_for_runtime(runtime="local-subprocess", framework=framework),
    artifacts=[],
)
Path(args.artifact_manifest).write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
Path(args.events).write_text("", encoding="utf-8")
sys.exit(1)
"""
    runner = LocalProcessRunner(
        launcher=LocalLauncher(workspace_root=tmp_path),
        command=[sys.executable, "-c", script],
    )

    with pytest.raises(AppError) as exc_info:
        runner.execute(handoff)

    assert exc_info.value.code == "tool_backend_error"
    assert exc_info.value.context["order_id"] == "ORD-ERR-100"


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


def test_k8s_launcher_mounts_common_parent_including_runtime_result_path():
    payload = _runner_spec().model_copy(
        update={
            "bootstrap": RunnerBootstrapPaths(
                run_spec_path="/workspace/input/run_spec.json",
                events_path="/workspace/output/events/events.ndjson",
                runtime_result_path="/workspace/output/runtime/results/runtime_result.json",
                terminal_result_path="/workspace/output/runtime/terminal/terminal_result.json",
                artifact_manifest_path=(
                    "/workspace/output/runtime/artifacts/artifact_manifest.json"
                ),
                artifact_dir="/workspace/output/runtime/artifacts/files",
            ),
            "executor_config": {
                "backend": "k8s-job",
                "runner_image": "ghcr.io/example/atlas-runner:latest",
                "metadata": {"command": ["python", "-m", "atlas_runner"]},
            },
        }
    )

    request = K8sLauncher(namespace="atlas-tests").build_request(payload)

    container = request.job_manifest["spec"]["template"]["spec"]["containers"][0]
    assert container["volumeMounts"][1]["mountPath"] == "/workspace/output"
