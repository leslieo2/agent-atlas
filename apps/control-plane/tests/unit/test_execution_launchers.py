from __future__ import annotations

import json
import subprocess
import sys
import tarfile
from pathlib import Path
from uuid import uuid4

import pytest
from agent_atlas_contracts.execution import (
    RUNNER_CALLBACK_PREFIX,
    ArtifactManifest,
    EventEnvelope,
    ExecutionArtifact,
    ProducerInfo,
    RunnerBootstrapPaths,
    RunnerRunSpec,
    TerminalMetrics,
    TerminalResult,
)
from agent_atlas_runner_base import materialization as runner_materialization
from agent_atlas_runner_base.claude_code import main as claude_code_runner_main
from app.core.errors import AgentFrameworkMismatchError, AppError
from app.execution.adapters import (
    DockerContainerRunner,
    K8sContainerRunner,
    K8sLauncher,
    LocalLauncher,
    LocalProcessRunner,
    runner_run_spec_from_run_spec,
)
from app.execution.adapters.k8s_runner import K8sJobSnapshot
from app.execution.application.results import (
    PublishedRunExecutionResult,
    RuntimeExecutionResult,
)
from app.execution.contracts import ExecutionRunSpec
from app.modules.runs.domain.models import RunRecord
from app.modules.runs.domain.policies import RunAggregate
from app.modules.shared.domain.enums import AdapterKind, RunStatus, StepType
from app.modules.shared.domain.models import ProvenanceMetadata
from app.modules.shared.domain.traces import TraceIngestEvent


def _runner_spec() -> RunnerRunSpec:
    run_id = uuid4()
    published_agent_snapshot = {
        "manifest": {
            "agent_id": "triage-bot",
            "name": "Triage Bot",
            "description": "Checks incidents",
            "framework": AdapterKind.OPENAI_AGENTS.value,
            "default_model": "gpt-5.4-mini",
            "tags": [],
        },
        "entrypoint": "app.agent_plugins.basic:build_agent",
    }
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
                published_agent_snapshot=published_agent_snapshot,
                artifact_ref="source://triage-bot@fingerprint",
            ),
        ),
        artifact=ExecutionArtifact(
            framework=AdapterKind.OPENAI_AGENTS.value,
            entrypoint="app.agent_plugins.basic:build_agent",
            source_fingerprint="fingerprint",
            artifact_ref="source://triage-bot@fingerprint",
            image_ref=None,
            published_agent_snapshot=published_agent_snapshot,
        ),
        runner_backend="local-process",
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
    payload = payload.model_copy(
        update={
            "runner_backend": "local-process",
            "executor_config": {**dict(payload.executor_config), "runner_mode": "in-process"},
        }
    )

    runner = LocalProcessRunner(
        launcher=LocalLauncher(workspace_root=tmp_path),
        published_runtime=StubPublishedRuntime(),
    )

    result = runner.execute(payload)

    assert result.execution.runtime_result.output
    assert result.execution.runtime_result.provider == "stub"
    materialized_root = next(tmp_path.glob(f"{payload.run_id}/*"))
    assert materialized_root.joinpath("workspace/output/runtime_result.json").exists()
    assert materialized_root.joinpath("workspace/output/terminal_result.json").exists()


def test_local_process_runner_preserves_runtime_metadata_from_subprocess(tmp_path):
    payload = _runner_spec()
    payload = payload.model_copy(update={"runner_backend": "local-process"})
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

    result = runner.execute(payload)

    assert result.execution.runtime_result.execution_backend == "langgraph"
    assert result.execution.runtime_result.container_image == "ghcr.io/example/runner:123"
    assert result.execution.runtime_result.resolved_model == "gpt-5.4-mini-resolved"


def test_docker_container_runner_executes_runner_image_with_local_launcher(
    tmp_path,
    monkeypatch,
):
    payload = _runner_spec().model_copy(
        update={
            "runner_backend": "docker-container",
            "executor_config": {
                **dict(_runner_spec().executor_config),
                "backend": "external-runner",
                "runner_image": "atlas-claude-validation:local",
                "metadata": {
                    "runner_backend": "docker-container",
                    "claude_code_cli": {
                        "command": "claude",
                        "args": ["--dangerously-skip-permissions"],
                        "version": "starter",
                    },
                },
            },
        }
    )

    monkeypatch.setattr(
        "app.execution.adapters.runner._copy_claude_auth_material",
        lambda target_home: target_home.mkdir(parents=True, exist_ok=True),
    )
    monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "token-from-host")

    def _fake_run(cmd, *, capture_output, text, check):
        assert capture_output is True
        assert text is True
        assert check is False
        assert cmd[:2] == ["docker", "run"]
        assert "atlas-claude-validation:local" in cmd
        mounts = {
            cmd[index + 1].split(":", 1)[1]: Path(cmd[index + 1].split(":", 1)[0])
            for index, arg in enumerate(cmd)
            if arg == "-v"
        }
        input_dir = mounts["/workspace/input"]
        output_dir = mounts["/workspace/output"]
        run_spec = RunnerRunSpec.model_validate_json(
            input_dir.joinpath("run_spec.json").read_text(encoding="utf-8")
        )
        assert (
            run_spec.executor_config["metadata"]["claude_code_cli"]["env"]["ANTHROPIC_AUTH_TOKEN"]
            == "token-from-host"
        )
        runtime_result = RuntimeExecutionResult(
            output="after",
            latency_ms=17,
            token_usage=0,
            provider="claude-code-cli",
            execution_backend="external-runner",
            resolved_model=run_spec.model,
        )
        output_dir.joinpath("runtime_result.json").write_text(
            runtime_result.model_dump_json(indent=2),
            encoding="utf-8",
        )
        terminal_result = TerminalResult(
            run_id=run_spec.run_id,
            experiment_id=run_spec.experiment_id,
            attempt=run_spec.attempt,
            attempt_id=run_spec.attempt_id,
            status="succeeded",
            output="after",
            producer=ProducerInfo(runtime="claude-code-cli", framework=run_spec.framework),
            metrics=TerminalMetrics(latency_ms=17, token_usage=0, tool_calls=0),
        )
        output_dir.joinpath("terminal_result.json").write_text(
            terminal_result.model_dump_json(indent=2),
            encoding="utf-8",
        )
        artifact_manifest = ArtifactManifest(
            run_id=run_spec.run_id,
            experiment_id=run_spec.experiment_id,
            attempt=run_spec.attempt,
            attempt_id=run_spec.attempt_id,
            producer=ProducerInfo(runtime="claude-code-cli", framework=run_spec.framework),
            artifacts=[],
        )
        output_dir.joinpath("artifact_manifest.json").write_text(
            artifact_manifest.model_dump_json(indent=2),
            encoding="utf-8",
        )
        output_dir.joinpath("events.ndjson").write_text("", encoding="utf-8")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr("app.execution.adapters.runner.subprocess.run", _fake_run)

    runner = DockerContainerRunner(launcher=LocalLauncher(workspace_root=tmp_path))
    result = runner.execute(payload)

    assert result.runner_backend == "docker-container"
    assert result.execution.runtime_result.container_image == "atlas-claude-validation:local"
    assert result.execution.runtime_result.execution_backend == "external-runner"


def test_local_process_runner_rehydrates_serialized_app_error(tmp_path):
    payload = _runner_spec()
    payload = payload.model_copy(update={"runner_backend": "local-process"})
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
        runner.execute(payload)

    assert exc_info.value.context["agent_id"] == "triage-bot"
    assert exc_info.value.context["expected_framework"] == "openai-agents-sdk"
    assert exc_info.value.context["actual_framework"] == "langgraph"


def test_local_process_runner_preserves_unknown_app_error_codes(tmp_path):
    payload = _runner_spec()
    payload = payload.model_copy(update={"runner_backend": "local-process"})
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
        runner.execute(payload)

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
    assert request.env["ATLAS_RUNNER_CALLBACK_MODE"] == "stdout-jsonl"
    assert request.args[:2] == ["--run-spec", "/workspace/input/run_spec.json"]
    assert request.config_map_manifest["data"]["run_spec.json"]
    container = request.job_manifest["spec"]["template"]["spec"]["containers"][0]
    assert container["command"] == ["python", "-m", "atlas_runner"]
    assert container["volumeMounts"][0]["mountPath"] == "/workspace/input/run_spec.json"
    assert container["volumeMounts"][1]["mountPath"] == "/workspace/output"
    assert request.job_manifest["spec"]["activeDeadlineSeconds"] == 600


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


def test_k8s_launcher_uses_claude_code_stream_json_entrypoint_for_external_runner():
    payload = _runner_spec().model_copy(
        update={
            "runner_backend": "k8s-container",
            "executor_config": {
                "backend": "external-runner",
                "runner_image": "ghcr.io/example/claude-runner:latest",
                "metadata": {
                    "runner_backend": "k8s-container",
                    "claude_code_cli": {
                        "command": "claude",
                        "args": ["--allowedTools", "Read"],
                        "version": "1.0.0",
                    },
                },
            },
        }
    )

    request = K8sLauncher(namespace="atlas-tests").build_request(payload)

    container = request.job_manifest["spec"]["template"]["spec"]["containers"][0]
    assert container["command"] == [sys.executable, "-m", "agent_atlas_runner_base.claude_code"]
    assert request.image == "ghcr.io/example/claude-runner:latest"
    assert request.args[:2] == ["--run-spec", "/workspace/input/run_spec.json"]


def test_k8s_container_runner_collects_callback_outputs_and_persists_artifacts(tmp_path):
    payload = _runner_spec().model_copy(
        update={
            "runner_backend": "k8s-container",
            "image_ref": "ghcr.io/example/published-agent:123",
            "executor_config": {
                "backend": "k8s-job",
                "runner_image": "ghcr.io/example/atlas-runner:latest",
                "timeout_seconds": 30,
                "artifact_path": str(tmp_path / "atlas-artifacts"),
                "metadata": {"command": ["python", "-m", "atlas_runner"]},
            },
        }
    )
    run = RunAggregate.create(
        ExecutionRunSpec(
            run_id=payload.run_id,
            experiment_id=payload.experiment_id,
            project=payload.project,
            dataset=payload.dataset,
            agent_id=payload.agent_id,
            model=payload.model,
            entrypoint=payload.entrypoint,
            agent_type=AdapterKind.OPENAI_AGENTS,
            input_summary="k8s run",
            prompt=payload.prompt,
        )
    ).model_copy(update={"status": RunStatus.RUNNING})

    class StubRunRepository:
        def __init__(self, saved_run: RunRecord) -> None:
            self.saved = saved_run

        def get(self, run_id):
            return self.saved if run_id == self.saved.run_id else None

        def list(self):
            return [self.saved]

        def save(self, run: RunRecord) -> None:
            self.saved = run

    event = EventEnvelope(
        run_id=payload.run_id,
        experiment_id=payload.experiment_id,
        attempt=payload.attempt,
        attempt_id=payload.attempt_id,
        event_id="evt-1",
        sequence=1,
        event_type="tool.succeeded",
        producer=ProducerInfo(runtime="openai-agents-sdk", framework=payload.framework),
        payload={"output": {"success": True}},
    )
    runtime_result = RuntimeExecutionResult(
        output="k8s ok",
        latency_ms=12,
        token_usage=34,
        provider="openai-agents-sdk",
    )
    terminal_result = TerminalResult(
        run_id=payload.run_id,
        experiment_id=payload.experiment_id,
        attempt=payload.attempt,
        attempt_id=payload.attempt_id,
        status="succeeded",
        producer=ProducerInfo(runtime="openai-agents-sdk", framework=payload.framework),
        metrics=TerminalMetrics(latency_ms=12, token_usage=34, tool_calls=1),
    )
    manifest = ArtifactManifest(
        run_id=payload.run_id,
        experiment_id=payload.experiment_id,
        attempt=payload.attempt,
        attempt_id=payload.attempt_id,
        producer=ProducerInfo(runtime="openai-agents-sdk", framework=payload.framework),
        artifacts=[
            {
                "path": "reports/summary.txt",
                "kind": "file",
                "media_type": "text/plain",
            }
        ],
    )
    callback_logs = "\n".join(
        [
            RUNNER_CALLBACK_PREFIX
            + json.dumps({"kind": "event_envelope", "payload": event.model_dump(mode="json")}),
            RUNNER_CALLBACK_PREFIX
            + json.dumps(
                {"kind": "runtime_result", "payload": runtime_result.model_dump(mode="json")}
            ),
            RUNNER_CALLBACK_PREFIX
            + json.dumps(
                {"kind": "terminal_result", "payload": terminal_result.model_dump(mode="json")}
            ),
            RUNNER_CALLBACK_PREFIX
            + json.dumps(
                {"kind": "artifact_manifest", "payload": manifest.model_dump(mode="json")}
            ),
        ]
    )

    class StubKubectlClient:
        def __init__(self) -> None:
            self.applied: list[dict[str, object]] = []
            self.deleted: list[tuple[str, str, str]] = []
            self.snapshots = iter(
                [
                    K8sJobSnapshot(phase="starting", pod_name="atlas-pod", pod_phase="Pending"),
                    K8sJobSnapshot(phase="running", pod_name="atlas-pod", pod_phase="Running"),
                    K8sJobSnapshot(
                        phase="succeeded",
                        pod_name="atlas-pod",
                        pod_phase="Succeeded",
                        exit_code=0,
                    ),
                    K8sJobSnapshot(
                        phase="succeeded",
                        pod_name="atlas-pod",
                        pod_phase="Succeeded",
                        exit_code=0,
                    ),
                ]
            )

        def apply_manifest(self, manifest):
            self.applied.append(manifest)

        def delete_resource(self, *, kind: str, name: str, namespace: str, ignore_not_found=True):
            self.deleted.append((kind, name, namespace))

        def get_job_snapshot(self, *, namespace: str, job_name: str):
            del namespace, job_name
            return next(self.snapshots)

        def read_logs(self, *, namespace: str, pod_name: str | None) -> str:
            del namespace, pod_name
            return callback_logs

        def copy_from_pod(
            self,
            *,
            namespace: str,
            pod_name: str | None,
            source_path: str,
            target_path,
        ) -> bool:
            del namespace, pod_name, source_path
            target_path.mkdir(parents=True, exist_ok=True)
            target_path.joinpath("reports").mkdir(parents=True, exist_ok=True)
            target_path.joinpath("reports/summary.txt").write_text("copied", encoding="utf-8")
            return True

    repository = StubRunRepository(run)
    runner = K8sContainerRunner(
        run_repository=repository,
        launcher=K8sLauncher(namespace="atlas-tests"),
        client=StubKubectlClient(),
        poll_interval_seconds=0.01,
        heartbeat_interval_seconds=0.01,
    )

    result = runner.execute(payload)

    assert result.runner_backend == "k8s-container"
    assert result.execution.runtime_result.execution_backend == "kubernetes-job"
    assert result.execution.runtime_result.container_image == "ghcr.io/example/atlas-runner:latest"
    assert result.execution.terminal_result is not None
    assert result.execution.terminal_result.metrics.tool_calls == 1
    assert len(result.execution.event_envelopes) == 1
    assert result.execution.artifact_manifest is not None
    assert result.execution.artifact_manifest.artifacts[0].uri is not None
    artifact_file = tmp_path.joinpath(
        "atlas-artifacts",
        str(payload.run_id),
        str(payload.attempt_id),
        "artifacts",
        "reports",
        "summary.txt",
    )
    assert artifact_file.read_text(encoding="utf-8") == "copied"
    assert repository.saved.last_heartbeat_at is not None
    assert repository.saved.lease_expires_at is not None
    assert repository.saved.execution_backend == "kubernetes-job"


def test_k8s_launcher_requires_explicit_runner_image_even_when_published_image_exists():
    payload = _runner_spec().model_copy(
        update={
            "image_ref": "ghcr.io/example/published-agent:123",
            "executor_config": {
                "backend": "k8s-job",
                "metadata": {"command": ["python", "-m", "atlas_runner"]},
            },
        }
    )

    with pytest.raises(ValueError, match="runner_image"):
        K8sLauncher(namespace="atlas-tests").build_request(payload)


def test_claude_code_stream_json_runner_writes_neutral_outputs(tmp_path):
    payload = _runner_spec().model_copy(
        update={
            "runner_backend": "k8s-container",
            "executor_config": {
                "backend": "external-runner",
                "runner_image": "ghcr.io/example/claude-runner:latest",
                "metadata": {
                    "runner_backend": "k8s-container",
                    "claude_code_cli": {
                        "command": sys.executable,
                        "args": [
                            "-c",
                            (
                                "import json, os, sys; "
                                "payload = {'argv': sys.argv[1:], "
                                "'env': os.getenv('ANTHROPIC_AUTH_TOKEN')}; "
                                "assistant = {'type':'assistant', "
                                "'message':json.dumps(payload)}; "
                                "print(json.dumps(assistant)); "
                                "print(json.dumps({'type':'result','result':'done'}))"
                            ),
                        ],
                        "env": {"ANTHROPIC_AUTH_TOKEN": "token-from-config"},
                        "profile": "starter",
                        "version": "1.2.3",
                    },
                },
            },
            "bootstrap": RunnerBootstrapPaths(
                run_spec_path=str(tmp_path / "workspace/input/run_spec.json"),
                events_path=str(tmp_path / "workspace/output/events.ndjson"),
                runtime_result_path=str(tmp_path / "workspace/output/runtime_result.json"),
                terminal_result_path=str(tmp_path / "workspace/output/terminal_result.json"),
                artifact_manifest_path=str(tmp_path / "workspace/output/artifact_manifest.json"),
                artifact_dir=str(tmp_path / "workspace/output/artifacts"),
            ),
        }
    )
    Path(payload.bootstrap.run_spec_path).parent.mkdir(parents=True, exist_ok=True)
    Path(payload.bootstrap.run_spec_path).write_text(
        payload.model_dump_json(indent=2),
        encoding="utf-8",
    )

    exit_code = claude_code_runner_main(
        [
            "--run-spec",
            payload.bootstrap.run_spec_path,
            "--events",
            payload.bootstrap.events_path,
            "--runtime-result",
            payload.bootstrap.runtime_result_path,
            "--terminal-result",
            payload.bootstrap.terminal_result_path,
            "--artifact-manifest",
            payload.bootstrap.artifact_manifest_path,
            "--artifact-dir",
            payload.bootstrap.artifact_dir,
        ]
    )

    assert exit_code == 0
    runtime_result = json.loads(
        Path(payload.bootstrap.runtime_result_path).read_text(encoding="utf-8")
    )
    terminal_result = json.loads(
        Path(payload.bootstrap.terminal_result_path).read_text(encoding="utf-8")
    )
    manifest = json.loads(
        Path(payload.bootstrap.artifact_manifest_path).read_text(encoding="utf-8")
    )
    events = [
        json.loads(line)
        for line in Path(payload.bootstrap.events_path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    assert runtime_result["provider"] == "claude-code-cli"
    assert runtime_result["output"] == "done"
    assert runtime_result["execution_backend"] == "kubernetes-job"
    assert terminal_result["status"] == "succeeded"
    assert terminal_result["producer"]["version"] == "1.2.3"
    assert len(events) == 2
    event_payload = json.loads(events[0]["payload"]["output"]["output"])
    assert event_payload["env"] == "token-from-config"
    assert event_payload["argv"][-1] == "Summarize the incident."
    assert "--model" not in event_payload["argv"]
    assert event_payload["argv"][:2] == ["--print", "--verbose"]
    assert "--profile" in event_payload["argv"]
    assert manifest["artifacts"][0]["path"] == "transcripts/claude-stream.jsonl"


def test_claude_code_stream_json_runner_materializes_project_bundle_and_tracks_changed_files(
    tmp_path,
    monkeypatch,
):
    source_project = tmp_path / "source-project"
    source_project.mkdir(parents=True, exist_ok=True)
    source_project.joinpath("main.py").write_text("print('before')\n", encoding="utf-8")
    bundle_path = tmp_path / "project-bundle.tar.gz"
    with tarfile.open(bundle_path, "w:gz") as archive:
        archive.add(source_project, arcname="demo-project")

    mount_path = tmp_path / "workspace/project"
    monkeypatch.setattr(runner_materialization, "WORKSPACE_PROJECT_MOUNT_PATH", mount_path)
    payload = _runner_spec().model_copy(
        update={
            "runner_backend": "k8s-container",
            "executor_config": {
                "backend": "external-runner",
                "runner_image": "ghcr.io/example/claude-runner:latest",
                "metadata": {
                    "runner_backend": "k8s-container",
                    "project_materialization": {
                        "mode": "artifact_bundle",
                        "artifact_ref": f"file://{bundle_path}",
                        "mount_path": "/workspace/project",
                    },
                    "claude_code_cli": {
                        "command": sys.executable,
                        "args": [
                            "-c",
                            (
                                "from pathlib import Path; "
                                "import json; "
                                "target = Path('main.py'); "
                                "target.write_text(\"print('after')\\n\", encoding='utf-8'); "
                                "print(json.dumps({'type':'result','result':'edited'}))"
                            ),
                        ],
                        "version": "1.2.3",
                    },
                },
            },
            "bootstrap": RunnerBootstrapPaths(
                run_spec_path=str(tmp_path / "workspace/input/run_spec.json"),
                events_path=str(tmp_path / "workspace/output/events.ndjson"),
                runtime_result_path=str(tmp_path / "workspace/output/runtime_result.json"),
                terminal_result_path=str(tmp_path / "workspace/output/terminal_result.json"),
                artifact_manifest_path=str(tmp_path / "workspace/output/artifact_manifest.json"),
                artifact_dir=str(tmp_path / "workspace/output/artifacts"),
            ),
        }
    )
    Path(payload.bootstrap.run_spec_path).parent.mkdir(parents=True, exist_ok=True)
    Path(payload.bootstrap.run_spec_path).write_text(
        payload.model_dump_json(indent=2),
        encoding="utf-8",
    )

    exit_code = claude_code_runner_main(
        [
            "--run-spec",
            payload.bootstrap.run_spec_path,
            "--events",
            payload.bootstrap.events_path,
            "--runtime-result",
            payload.bootstrap.runtime_result_path,
            "--terminal-result",
            payload.bootstrap.terminal_result_path,
            "--artifact-manifest",
            payload.bootstrap.artifact_manifest_path,
            "--artifact-dir",
            payload.bootstrap.artifact_dir,
        ]
    )

    assert exit_code == 0
    assert mount_path.joinpath("main.py").read_text(encoding="utf-8") == "print('after')\n"
    manifest = json.loads(
        Path(payload.bootstrap.artifact_manifest_path).read_text(encoding="utf-8")
    )
    changed_files_artifact = next(
        item for item in manifest["artifacts"] if item["path"] == "workspace/changed-files.json"
    )
    changed_manifest = json.loads(
        Path(payload.bootstrap.artifact_dir, changed_files_artifact["path"]).read_text(
            encoding="utf-8"
        )
    )
    assert changed_manifest["modified"] == ["main.py"]


def test_claude_code_stream_json_runner_surfaces_materialization_failures_as_neutral_outputs(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(
        runner_materialization,
        "WORKSPACE_PROJECT_MOUNT_PATH",
        tmp_path / "workspace/project",
    )
    payload = _runner_spec().model_copy(
        update={
            "runner_backend": "k8s-container",
            "executor_config": {
                "backend": "external-runner",
                "runner_image": "ghcr.io/example/claude-runner:latest",
                "metadata": {
                    "runner_backend": "k8s-container",
                    "project_materialization": {
                        "mode": "artifact_bundle",
                        "artifact_ref": f"file://{tmp_path / 'missing-bundle.tar.gz'}",
                        "mount_path": "/workspace/project",
                    },
                    "claude_code_cli": {
                        "command": sys.executable,
                        "args": ["-c", "print('should-not-run')"],
                        "version": "1.2.3",
                    },
                },
            },
            "bootstrap": RunnerBootstrapPaths(
                run_spec_path=str(tmp_path / "workspace/input/run_spec.json"),
                events_path=str(tmp_path / "workspace/output/events.ndjson"),
                runtime_result_path=str(tmp_path / "workspace/output/runtime_result.json"),
                terminal_result_path=str(tmp_path / "workspace/output/terminal_result.json"),
                artifact_manifest_path=str(tmp_path / "workspace/output/artifact_manifest.json"),
                artifact_dir=str(tmp_path / "workspace/output/artifacts"),
            ),
        }
    )
    Path(payload.bootstrap.run_spec_path).parent.mkdir(parents=True, exist_ok=True)
    Path(payload.bootstrap.run_spec_path).write_text(
        payload.model_dump_json(indent=2),
        encoding="utf-8",
    )

    exit_code = claude_code_runner_main(
        [
            "--run-spec",
            payload.bootstrap.run_spec_path,
            "--events",
            payload.bootstrap.events_path,
            "--runtime-result",
            payload.bootstrap.runtime_result_path,
            "--terminal-result",
            payload.bootstrap.terminal_result_path,
            "--artifact-manifest",
            payload.bootstrap.artifact_manifest_path,
            "--artifact-dir",
            payload.bootstrap.artifact_dir,
        ]
    )

    assert exit_code == 1
    runtime_result = json.loads(
        Path(payload.bootstrap.runtime_result_path).read_text(encoding="utf-8")
    )
    terminal_result = json.loads(
        Path(payload.bootstrap.terminal_result_path).read_text(encoding="utf-8")
    )
    manifest = json.loads(
        Path(payload.bootstrap.artifact_manifest_path).read_text(encoding="utf-8")
    )

    assert runtime_result["execution_backend"] == "kubernetes-job"
    assert terminal_result["status"] == "failed"
    assert terminal_result["reason_code"] == "workspace_materialization_failed"
    assert manifest["artifacts"][0]["path"] == "logs/materialization-error.txt"


def test_claude_code_stream_json_runner_rejects_noncanonical_mount_path(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(
        runner_materialization,
        "WORKSPACE_PROJECT_MOUNT_PATH",
        tmp_path / "workspace/project",
    )
    payload = _runner_spec().model_copy(
        update={
            "runner_backend": "k8s-container",
            "executor_config": {
                "backend": "external-runner",
                "runner_image": "ghcr.io/example/claude-runner:latest",
                "metadata": {
                    "runner_backend": "k8s-container",
                    "project_materialization": {
                        "mode": "artifact_bundle",
                        "artifact_ref": f"file://{tmp_path / 'bundle.tar.gz'}",
                        "mount_path": str(tmp_path / "custom-workspace"),
                    },
                    "claude_code_cli": {
                        "command": sys.executable,
                        "args": ["-c", "print('should-not-run')"],
                        "version": "1.2.3",
                    },
                },
            },
            "bootstrap": RunnerBootstrapPaths(
                run_spec_path=str(tmp_path / "workspace/input/run_spec.json"),
                events_path=str(tmp_path / "workspace/output/events.ndjson"),
                runtime_result_path=str(tmp_path / "workspace/output/runtime_result.json"),
                terminal_result_path=str(tmp_path / "workspace/output/terminal_result.json"),
                artifact_manifest_path=str(tmp_path / "workspace/output/artifact_manifest.json"),
                artifact_dir=str(tmp_path / "workspace/output/artifacts"),
            ),
        }
    )
    Path(payload.bootstrap.run_spec_path).parent.mkdir(parents=True, exist_ok=True)
    Path(payload.bootstrap.run_spec_path).write_text(
        payload.model_dump_json(indent=2),
        encoding="utf-8",
    )

    exit_code = claude_code_runner_main(
        [
            "--run-spec",
            payload.bootstrap.run_spec_path,
            "--events",
            payload.bootstrap.events_path,
            "--runtime-result",
            payload.bootstrap.runtime_result_path,
            "--terminal-result",
            payload.bootstrap.terminal_result_path,
            "--artifact-manifest",
            payload.bootstrap.artifact_manifest_path,
            "--artifact-dir",
            payload.bootstrap.artifact_dir,
        ]
    )

    assert exit_code == 1
    terminal_result = json.loads(
        Path(payload.bootstrap.terminal_result_path).read_text(encoding="utf-8")
    )
    assert terminal_result["reason_code"] == "workspace_materialization_failed"
    assert "mount_path=/workspace/project" in terminal_result["reason_message"]
