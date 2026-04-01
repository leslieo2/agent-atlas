from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

from agent_atlas_contracts.execution import (
    RUNNER_CALLBACK_PREFIX,
    ArtifactManifest,
    EventEnvelope,
    ProducerInfo,
    RunnerRunSpec,
    TerminalMetrics,
    TerminalResult,
)
from app.bootstrap.container import get_container
from app.execution.adapters.k8s_runner import K8sJobSnapshot
from app.execution.application.results import RuntimeExecutionResult


class FakeKubectlK8sClient:
    def __init__(
        self,
        *,
        outputs: Mapping[str, str],
        artifact_contents: Mapping[str, str] | None = None,
    ) -> None:
        self.outputs = dict(outputs)
        self.artifact_contents = dict(artifact_contents or {})
        self._config_specs: dict[str, RunnerRunSpec] = {}
        self._job_specs: dict[str, RunnerRunSpec] = {}
        self._job_snapshots: dict[str, int] = {}

    def apply_manifest(self, manifest: dict[str, object]) -> None:
        kind = manifest.get("kind")
        metadata = manifest.get("metadata")
        if not isinstance(metadata, dict):
            return
        name = metadata.get("name")
        if not isinstance(name, str) or not name.strip():
            return
        if kind == "ConfigMap":
            data = manifest.get("data")
            if not isinstance(data, dict):
                return
            payload = data.get("run_spec.json")
            if not isinstance(payload, str):
                return
            self._config_specs[name] = RunnerRunSpec.model_validate_json(payload)
            return
        if kind == "Job":
            spec = manifest.get("spec")
            if not isinstance(spec, dict):
                return
            template = spec.get("template")
            if not isinstance(template, dict):
                return
            pod_spec = template.get("spec")
            if not isinstance(pod_spec, dict):
                return
            volumes = pod_spec.get("volumes")
            if not isinstance(volumes, list):
                return
            config_map_name = None
            for volume in volumes:
                if not isinstance(volume, dict):
                    continue
                config_map = volume.get("configMap")
                if not isinstance(config_map, dict):
                    continue
                candidate = config_map.get("name")
                if isinstance(candidate, str) and candidate.strip():
                    config_map_name = candidate
                    break
            if config_map_name is None:
                return
            run_spec = self._config_specs.get(config_map_name)
            if run_spec is None:
                return
            self._job_specs[name] = run_spec
            self._job_snapshots.setdefault(name, 0)

    def delete_resource(
        self,
        *,
        kind: str,
        name: str,
        namespace: str,
        ignore_not_found: bool = True,
    ) -> None:
        del kind, name, namespace, ignore_not_found
        return None

    def get_job_snapshot(self, *, namespace: str, job_name: str) -> K8sJobSnapshot:
        del namespace
        if job_name not in self._job_specs:
            return K8sJobSnapshot(phase="missing", reason="job_not_found")
        step = self._job_snapshots.get(job_name, 0)
        self._job_snapshots[job_name] = step + 1
        if step == 0:
            return K8sJobSnapshot(phase="starting", pod_name=f"{job_name}-pod", pod_phase="Pending")
        if step == 1:
            return K8sJobSnapshot(phase="running", pod_name=f"{job_name}-pod", pod_phase="Running")
        return K8sJobSnapshot(
            phase="succeeded",
            pod_name=f"{job_name}-pod",
            pod_phase="Succeeded",
            exit_code=0,
        )

    def read_logs(self, *, namespace: str, pod_name: str | None) -> str:
        del namespace
        if pod_name is None:
            return ""
        run_spec = self._job_specs.get(pod_name.removesuffix("-pod"))
        if run_spec is None:
            return ""
        output = self.outputs.get(run_spec.prompt, run_spec.prompt)
        runner_image = run_spec.executor_config.get("runner_image")
        metadata = run_spec.executor_config.get("metadata")
        claude_code_cli = metadata.get("claude_code_cli") if isinstance(metadata, dict) else None
        runtime_name = (
            "claude-code-cli" if isinstance(claude_code_cli, dict) else "openai-agents-sdk"
        )
        runtime_result = RuntimeExecutionResult(
            output=output,
            latency_ms=12,
            token_usage=21,
            provider=runtime_name,
            resolved_model=run_spec.model,
            execution_backend="kubernetes-job",
            container_image=runner_image if isinstance(runner_image, str) else None,
        )
        event = EventEnvelope(
            run_id=run_spec.run_id,
            experiment_id=run_spec.experiment_id,
            attempt=run_spec.attempt,
            attempt_id=run_spec.attempt_id,
            event_id=f"evt-{run_spec.run_id}",
            sequence=1,
            event_type="llm.response",
            producer=ProducerInfo(runtime=runtime_name, framework=run_spec.framework),
            payload={
                "step_type": "llm",
                "name": run_spec.model,
                "input": {"prompt": run_spec.prompt},
                "output": {"output": output, "success": True, "provider": runtime_name},
                "latency_ms": 12,
                "token_usage": 21,
            },
        )
        terminal_result = TerminalResult(
            run_id=run_spec.run_id,
            experiment_id=run_spec.experiment_id,
            attempt=run_spec.attempt,
            attempt_id=run_spec.attempt_id,
            status="succeeded",
            output=output,
            producer=ProducerInfo(runtime=runtime_name, framework=run_spec.framework),
            metrics=TerminalMetrics(latency_ms=12, token_usage=21, tool_calls=0),
        )
        artifact_manifest = ArtifactManifest(
            run_id=run_spec.run_id,
            experiment_id=run_spec.experiment_id,
            attempt=run_spec.attempt,
            attempt_id=run_spec.attempt_id,
            producer=ProducerInfo(runtime=runtime_name, framework=run_spec.framework),
            artifacts=[
                {
                    "path": "reports/summary.txt",
                    "kind": "file",
                    "media_type": "text/plain",
                    "metadata": {"kind": "summary"},
                },
                {
                    "path": "transcripts/claude-stream.jsonl",
                    "kind": "file",
                    "media_type": "application/x-ndjson",
                    "metadata": {"kind": "transcript", "runner_family": runtime_name},
                },
            ],
        )
        return "\n".join(
            [
                RUNNER_CALLBACK_PREFIX
                + json.dumps({"kind": "event_envelope", "payload": event.model_dump(mode="json")}),
                RUNNER_CALLBACK_PREFIX
                + json.dumps(
                    {"kind": "runtime_result", "payload": runtime_result.model_dump(mode="json")}
                ),
                RUNNER_CALLBACK_PREFIX
                + json.dumps(
                    {
                        "kind": "terminal_result",
                        "payload": terminal_result.model_dump(mode="json"),
                    }
                ),
                RUNNER_CALLBACK_PREFIX
                + json.dumps(
                    {
                        "kind": "artifact_manifest",
                        "payload": artifact_manifest.model_dump(mode="json"),
                    }
                ),
            ]
        )

    def copy_from_pod(
        self,
        *,
        namespace: str,
        pod_name: str | None,
        source_path: str,
        target_path: Path,
    ) -> bool:
        del namespace, source_path
        if pod_name is None:
            return False
        run_spec = self._job_specs.get(pod_name.removesuffix("-pod"))
        if run_spec is None:
            return False
        target_path.mkdir(parents=True, exist_ok=True)
        target_path.joinpath("reports").mkdir(parents=True, exist_ok=True)
        target_path.joinpath("transcripts").mkdir(parents=True, exist_ok=True)
        content = self.artifact_contents.get(
            run_spec.prompt, self.outputs.get(run_spec.prompt, "done")
        )
        target_path.joinpath("reports/summary.txt").write_text(content, encoding="utf-8")
        target_path.joinpath("transcripts/claude-stream.jsonl").write_text(
            json.dumps({"type": "result", "result": content}) + "\n",
            encoding="utf-8",
        )
        return True


def install_fake_k8s_runtime(
    monkeypatch,
    *,
    outputs: Mapping[str, str],
    artifact_contents: Mapping[str, str] | None = None,
) -> FakeKubectlK8sClient:
    container = get_container()
    runner = container.infrastructure.execution.runner.runners["k8s-container"]
    client = FakeKubectlK8sClient(outputs=outputs, artifact_contents=artifact_contents)
    monkeypatch.setattr(runner, "client", client)
    monkeypatch.setattr(runner, "poll_interval_seconds", 0.01)
    monkeypatch.setattr(runner, "heartbeat_interval_seconds", 0.01)
    return client
