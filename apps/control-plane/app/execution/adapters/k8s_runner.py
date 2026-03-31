from __future__ import annotations

import json
import subprocess  # nosec B404 - kubectl is an explicit control-plane dependency
import tempfile
import time
from collections import deque
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path
from typing import Any
from uuid import UUID

from agent_atlas_contracts.execution import (
    ArtifactManifest,
    EventEnvelope,
    RunnerRunSpec,
    TerminalMetrics,
    TerminalResult,
    parse_runner_callback,
)
from agent_atlas_contracts.runtime import (
    PublishedRunExecutionResult,
    RuntimeExecutionResult,
    empty_artifact_manifest,
    producer_for_runtime,
    terminal_result_from_runtime_result,
)
from agent_atlas_runner_base.launchers import K8sLauncher

from app.core.errors import AppError, ProviderTimeoutError
from app.execution.application.results import ExecutionCancelled, RunnerExecutionResult
from app.modules.runs.application.ports import RunRepository
from app.modules.shared.domain.enums import RunStatus
from app.modules.shared.domain.models import utc_now


class SerializedK8sAppError(AppError):
    def __init__(
        self,
        *,
        code: str,
        message: str,
        context: dict[str, str] | None = None,
    ) -> None:
        self.code = code
        super().__init__(message, **dict(context or {}))


@dataclass(frozen=True)
class K8sJobSnapshot:
    phase: str
    pod_name: str | None = None
    pod_phase: str | None = None
    exit_code: int | None = None
    reason: str | None = None
    message: str | None = None


class KubectlK8sClient:
    def __init__(self, *, command: Sequence[str] | None = None) -> None:
        self.command = list(command) if command is not None else ["kubectl"]

    def apply_manifest(self, manifest: dict[str, Any]) -> None:
        self._run(["apply", "-f", "-"], input_text=json.dumps(manifest))

    def delete_resource(
        self,
        *,
        kind: str,
        name: str,
        namespace: str,
        ignore_not_found: bool = True,
    ) -> None:
        args = ["delete", kind, name, "--namespace", namespace]
        if ignore_not_found:
            args.append("--ignore-not-found=true")
        self._run(args, allow_failure=ignore_not_found)

    def get_job_snapshot(self, *, namespace: str, job_name: str) -> K8sJobSnapshot:
        job = self._load_json(
            ["get", "job", job_name, "--namespace", namespace, "-o", "json"],
            allow_not_found=True,
        )
        if job is None:
            return K8sJobSnapshot(phase="missing", reason="job_not_found")

        pods = self._load_json(
            [
                "get",
                "pods",
                "--namespace",
                namespace,
                "--selector",
                f"job-name={job_name}",
                "-o",
                "json",
            ],
            allow_not_found=True,
        )
        selected_pod = self._select_pod(pods)
        status = job.get("status", {}) if isinstance(job, dict) else {}
        conditions = status.get("conditions", [])
        if not isinstance(conditions, list):
            conditions = []
        condition_map = {
            item.get("type"): item
            for item in conditions
            if isinstance(item, dict) and isinstance(item.get("type"), str)
        }

        phase = "pending"
        if (
            status.get("succeeded", 0) > 0
            or condition_map.get("Complete", {}).get("status") == "True"
        ):
            phase = "succeeded"
        elif status.get("failed", 0) > 0 or condition_map.get("Failed", {}).get("status") == "True":
            phase = "failed"
        elif selected_pod is not None:
            pod_phase = self._pod_phase(selected_pod)
            if pod_phase == "Running":
                phase = "running"
            elif pod_phase == "Pending":
                phase = "starting"

        reason, message, exit_code = self._pod_details(selected_pod)
        if reason is None or message is None:
            failed_condition = condition_map.get("Failed")
            if isinstance(failed_condition, dict):
                reason = reason or self._string_value(failed_condition.get("reason"))
                message = message or self._string_value(failed_condition.get("message"))

        return K8sJobSnapshot(
            phase=phase,
            pod_name=self._pod_name(selected_pod),
            pod_phase=self._pod_phase(selected_pod),
            exit_code=exit_code,
            reason=reason,
            message=message,
        )

    def read_logs(self, *, namespace: str, pod_name: str | None) -> str:
        if pod_name is None:
            return ""
        completed = self._run(
            [
                "logs",
                pod_name,
                "--namespace",
                namespace,
                "--container",
                "runner",
            ],
            allow_failure=True,
        )
        return completed.stdout

    def copy_from_pod(
        self,
        *,
        namespace: str,
        pod_name: str | None,
        source_path: str,
        target_path: Path,
    ) -> bool:
        if pod_name is None:
            return False
        target_path.parent.mkdir(parents=True, exist_ok=True)
        completed = self._run(
            [
                "cp",
                f"{namespace}/{pod_name}:{source_path}",
                str(target_path),
            ],
            allow_failure=True,
        )
        if completed.returncode == 0:
            return True
        stderr = completed.stderr.lower()
        if "no such file or directory" in stderr or "cannot stat" in stderr:
            return False
        raise RuntimeError(
            completed.stderr.strip() or completed.stdout.strip() or "kubectl cp failed"
        )

    def _load_json(self, args: list[str], *, allow_not_found: bool) -> dict[str, Any] | None:
        completed = self._run(args, allow_failure=allow_not_found)
        if completed.returncode != 0:
            stderr = completed.stderr.lower()
            if allow_not_found and "notfound" in stderr.replace(" ", ""):
                return None
            raise RuntimeError(completed.stderr.strip() or completed.stdout.strip())
        payload = completed.stdout.strip()
        if not payload:
            return None
        loaded = json.loads(payload)
        return loaded if isinstance(loaded, dict) else None

    def _run(
        self,
        args: list[str],
        *,
        input_text: str | None = None,
        allow_failure: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        completed = subprocess.run(  # nosec B603
            [*self.command, *args],
            input=input_text,
            text=True,
            capture_output=True,
            check=False,
        )
        if completed.returncode != 0 and not allow_failure:
            message = completed.stderr.strip() or completed.stdout.strip() or "kubectl failed"
            raise RuntimeError(message)
        return completed

    @staticmethod
    def _select_pod(pods: dict[str, Any] | None) -> dict[str, Any] | None:
        if not isinstance(pods, dict):
            return None
        items = pods.get("items")
        if not isinstance(items, list) or not items:
            return None

        def sort_key(item: dict[str, Any]) -> tuple[int, str]:
            phase = KubectlK8sClient._pod_phase(item)
            normalized_phase = phase or ""
            priority = {"Running": 0, "Pending": 1, "Succeeded": 2, "Failed": 3}.get(
                normalized_phase,
                4,
            )
            created_at = (
                item.get("metadata", {}).get("creationTimestamp", "")
                if isinstance(item.get("metadata"), dict)
                else ""
            )
            return (priority, str(created_at))

        return sorted(
            [item for item in items if isinstance(item, dict)],
            key=sort_key,
        )[0]

    @staticmethod
    def _pod_name(pod: dict[str, Any] | None) -> str | None:
        if not isinstance(pod, dict):
            return None
        metadata = pod.get("metadata")
        if not isinstance(metadata, dict):
            return None
        name = metadata.get("name")
        return name if isinstance(name, str) and name.strip() else None

    @staticmethod
    def _pod_phase(pod: dict[str, Any] | None) -> str | None:
        if not isinstance(pod, dict):
            return None
        status = pod.get("status")
        if not isinstance(status, dict):
            return None
        phase = status.get("phase")
        return phase if isinstance(phase, str) and phase.strip() else None

    @staticmethod
    def _pod_details(pod: dict[str, Any] | None) -> tuple[str | None, str | None, int | None]:
        if not isinstance(pod, dict):
            return None, None, None
        status = pod.get("status")
        if not isinstance(status, dict):
            return None, None, None
        container_statuses = status.get("containerStatuses")
        if not isinstance(container_statuses, list) or not container_statuses:
            return None, None, None
        first = container_statuses[0]
        if not isinstance(first, dict):
            return None, None, None
        state = first.get("state")
        if not isinstance(state, dict):
            return None, None, None
        for key in ("terminated", "waiting", "running"):
            candidate = state.get(key)
            if not isinstance(candidate, dict):
                continue
            reason = KubectlK8sClient._string_value(candidate.get("reason"))
            message = KubectlK8sClient._string_value(candidate.get("message"))
            exit_code = candidate.get("exitCode")
            return reason, message, exit_code if isinstance(exit_code, int) else None
        return None, None, None

    @staticmethod
    def _string_value(value: object) -> str | None:
        if not isinstance(value, str):
            return None
        normalized = value.strip()
        return normalized or None


@dataclass
class K8sCallbackCollector:
    processed_line_count: int = 0
    event_envelopes: list[EventEnvelope] = field(default_factory=list)
    runtime_result: RuntimeExecutionResult | None = None
    terminal_result: TerminalResult | None = None
    artifact_manifest: ArtifactManifest | None = None
    stdout_tail: deque[str] = field(default_factory=lambda: deque(maxlen=20))

    def ingest_logs(self, raw_logs: str) -> bool:
        if not raw_logs:
            return False
        lines = raw_logs.splitlines()
        if len(lines) < self.processed_line_count:
            self.processed_line_count = 0
        new_lines = lines[self.processed_line_count :]
        self.processed_line_count = len(lines)
        progressed = False
        for line in new_lines:
            normalized = line.strip()
            if not normalized:
                continue
            progressed = True
            envelope = parse_runner_callback(normalized)
            if envelope is None:
                self.stdout_tail.append(normalized)
                continue
            kind = envelope.kind
            content = envelope.payload
            if not isinstance(content, dict):
                continue
            if kind == "event_envelope":
                self.event_envelopes.append(EventEnvelope.model_validate(content))
            elif kind == "runtime_result":
                self.runtime_result = RuntimeExecutionResult.model_validate(content)
            elif kind == "terminal_result":
                self.terminal_result = TerminalResult.model_validate(content)
            elif kind == "artifact_manifest":
                self.artifact_manifest = ArtifactManifest.model_validate(content)
        return progressed

    def stdout_output(self) -> str:
        return "\n".join(self.stdout_tail)


class K8sContainerRunner:
    def __init__(
        self,
        *,
        run_repository: RunRepository,
        launcher: K8sLauncher | None = None,
        client: KubectlK8sClient | None = None,
        poll_interval_seconds: float = 1.0,
        heartbeat_interval_seconds: float = 5.0,
    ) -> None:
        self.run_repository = run_repository
        self.launcher = launcher or K8sLauncher()
        self.client = client or KubectlK8sClient()
        self.poll_interval_seconds = poll_interval_seconds
        self.heartbeat_interval_seconds = heartbeat_interval_seconds

    @staticmethod
    def backend_name() -> str:
        return "k8s-container"

    def execute(self, payload: RunnerRunSpec) -> RunnerExecutionResult:
        request = self.launcher.build_request(payload)
        collector = K8sCallbackCollector()
        last_heartbeat_at = 0.0
        last_phase: str | None = None
        started = time.monotonic()
        keep_resources = self._keep_resources(payload)

        self.client.apply_manifest(request.config_map_manifest)
        try:
            self.client.apply_manifest(request.job_manifest)
            while True:
                if self._is_cancel_requested(payload.run_id):
                    self._delete_job(request)
                    raise ExecutionCancelled()

                snapshot = self.client.get_job_snapshot(
                    namespace=request.namespace,
                    job_name=request.job_name,
                )
                progressed = collector.ingest_logs(
                    self.client.read_logs(
                        namespace=request.namespace,
                        pod_name=snapshot.pod_name,
                    )
                )
                now = time.monotonic()
                if (
                    progressed
                    or snapshot.phase != last_phase
                    or now - last_heartbeat_at >= self.heartbeat_interval_seconds
                ):
                    self._record_heartbeat(
                        payload,
                        snapshot,
                        image=request.image,
                        progressed=progressed,
                    )
                    last_heartbeat_at = now
                    last_phase = snapshot.phase

                if snapshot.phase in {"succeeded", "failed"}:
                    break
                timeout_seconds = payload.executor_config.get("timeout_seconds")
                if not isinstance(timeout_seconds, int | float) or timeout_seconds <= 0:
                    timeout_seconds = 1.0
                if now - started > float(timeout_seconds):
                    self._delete_job(request)
                    raise ProviderTimeoutError("kubernetes runner timed out")
                time.sleep(max(self.poll_interval_seconds, 0.1))

            final_snapshot = self.client.get_job_snapshot(
                namespace=request.namespace,
                job_name=request.job_name,
            )
            collector.ingest_logs(
                self.client.read_logs(
                    namespace=request.namespace,
                    pod_name=final_snapshot.pod_name,
                )
            )
            artifact_manifest = self._persist_artifacts(
                payload=payload,
                namespace=request.namespace,
                pod_name=final_snapshot.pod_name,
                collector=collector,
            )
            execution = self._execution_result(
                payload=payload,
                image=request.image,
                collector=collector,
                artifact_manifest=artifact_manifest,
                snapshot=final_snapshot,
            )
            if (
                execution.terminal_result is not None
                and execution.terminal_result.status != "succeeded"
            ):
                self._raise_failure(
                    terminal_result=execution.terminal_result,
                    snapshot=final_snapshot,
                    stdout_output=collector.stdout_output(),
                    model=payload.model,
                )
            return RunnerExecutionResult(
                runner_backend=self.backend_name(),
                artifact_ref=payload.artifact_ref,
                image_ref=payload.image_ref,
                execution=execution,
            )
        finally:
            if not keep_resources:
                self._delete_job(request)
                self.client.delete_resource(
                    kind="configmap",
                    name=request.config_map_name,
                    namespace=request.namespace,
                )

    def _execution_result(
        self,
        *,
        payload: RunnerRunSpec,
        image: str,
        collector: K8sCallbackCollector,
        artifact_manifest: ArtifactManifest | None,
        snapshot: K8sJobSnapshot,
    ) -> PublishedRunExecutionResult:
        producer = (
            collector.terminal_result.producer
            if collector.terminal_result is not None
            else producer_for_runtime(runtime=self.backend_name(), framework=payload.framework)
        )
        runtime_result = collector.runtime_result
        if runtime_result is None:
            if collector.terminal_result is not None:
                runtime_result = RuntimeExecutionResult(
                    output=collector.terminal_result.output or collector.stdout_output(),
                    latency_ms=collector.terminal_result.metrics.latency_ms,
                    token_usage=collector.terminal_result.metrics.token_usage,
                    provider=collector.terminal_result.producer.runtime or self.backend_name(),
                    resolved_model=payload.model,
                )
            else:
                runtime_result = RuntimeExecutionResult(
                    output=collector.stdout_output(),
                    latency_ms=0,
                    token_usage=0,
                    provider=self.backend_name(),
                    resolved_model=payload.model,
                )
        runtime_result = runtime_result.model_copy(
            update={
                "execution_backend": runtime_result.execution_backend or "kubernetes-job",
                "container_image": runtime_result.container_image or image,
                "resolved_model": runtime_result.resolved_model or payload.model,
            }
        )

        terminal_result = collector.terminal_result
        if terminal_result is None and snapshot.phase == "succeeded":
            terminal_result = terminal_result_from_runtime_result(
                payload=payload,
                runtime_result=runtime_result,
                producer=producer,
                tool_calls=sum(
                    1 for event in collector.event_envelopes if event.event_type.startswith("tool.")
                ),
            )
        if terminal_result is None:
            reason_message = snapshot.message or snapshot.reason or "kubernetes runner failed"
            terminal_result = TerminalResult(
                run_id=payload.run_id,
                experiment_id=payload.experiment_id,
                attempt=payload.attempt,
                attempt_id=payload.attempt_id,
                status="failed",
                reason_code=snapshot.reason or "k8s_job_failed",
                reason_message=reason_message,
                exit_code=snapshot.exit_code,
                output=collector.stdout_output() or reason_message,
                producer=producer,
                metrics=TerminalMetrics(),
            )

        resolved_artifact_manifest = (
            artifact_manifest
            or collector.artifact_manifest
            or empty_artifact_manifest(
                payload=payload,
                producer=producer,
            )
        )
        return PublishedRunExecutionResult(
            runtime_result=runtime_result,
            event_envelopes=list(collector.event_envelopes),
            terminal_result=terminal_result,
            artifact_manifest=resolved_artifact_manifest,
        )

    def _persist_artifacts(
        self,
        *,
        payload: RunnerRunSpec,
        namespace: str,
        pod_name: str | None,
        collector: K8sCallbackCollector,
    ) -> ArtifactManifest | None:
        manifest = collector.artifact_manifest
        if manifest is None:
            return None
        artifact_dir = self._local_artifact_dir(payload)
        copied = self.client.copy_from_pod(
            namespace=namespace,
            pod_name=pod_name,
            source_path=payload.bootstrap.artifact_dir,
            target_path=artifact_dir,
        )
        if manifest.artifacts and not copied:
            raise RuntimeError("kubernetes runner produced artifact metadata but no artifact files")
        updated_artifacts = []
        for artifact in manifest.artifacts:
            local_path = artifact_dir / artifact.path
            if local_path.exists():
                updated_artifacts.append(
                    artifact.model_copy(update={"uri": local_path.resolve().as_uri()})
                )
            else:
                updated_artifacts.append(artifact)
        return manifest.model_copy(update={"artifacts": updated_artifacts})

    def _raise_failure(
        self,
        *,
        terminal_result: TerminalResult,
        snapshot: K8sJobSnapshot,
        stdout_output: str,
        model: str,
    ) -> None:
        serialized_error = self._deserialize_app_error(terminal_result=terminal_result, model=model)
        if serialized_error is not None:
            raise serialized_error
        if snapshot.reason and "deadline" in snapshot.reason.lower():
            raise ProviderTimeoutError(
                terminal_result.reason_message or "kubernetes runner timed out"
            )
        message = terminal_result.reason_message or stdout_output or "kubernetes runner failed"
        raise RuntimeError(message)

    @staticmethod
    def _deserialize_app_error(
        *,
        terminal_result: TerminalResult,
        model: str,
    ) -> AppError | None:
        reason_code = terminal_result.reason_code or ""
        if reason_code == ProviderTimeoutError.code:
            return ProviderTimeoutError(
                terminal_result.reason_message or "provider request timed out"
            )
        if reason_code and reason_code != "runner_subprocess_failed":
            return SerializedK8sAppError(
                code=reason_code,
                message=terminal_result.reason_message or "runner execution failed",
                context=dict(terminal_result.reason_context),
            )
        del model
        return None

    def _record_heartbeat(
        self,
        payload: RunnerRunSpec,
        snapshot: K8sJobSnapshot,
        *,
        image: str,
        progressed: bool,
    ) -> None:
        run = self.run_repository.get(payload.run_id)
        if run is None or run.status in {
            RunStatus.SUCCEEDED,
            RunStatus.FAILED,
            RunStatus.CANCELLED,
            RunStatus.LOST,
        }:
            return
        now = utc_now()
        updated = run.model_copy(
            update={
                "last_heartbeat_at": now,
                "last_progress_at": (
                    now if progressed or run.last_progress_at is None else run.last_progress_at
                ),
                "lease_expires_at": now
                + timedelta(seconds=max(int(self.heartbeat_interval_seconds * 2), 1)),
                "heartbeat_sequence": run.heartbeat_sequence + 1,
                "execution_backend": "kubernetes-job",
                "container_image": run.container_image or image,
            }
        )
        if updated.status not in {RunStatus.CANCELLING, RunStatus.CANCELLED}:
            if snapshot.phase == "running":
                updated.status = RunStatus.RUNNING
            elif snapshot.phase in {"pending", "starting"} and updated.status == RunStatus.QUEUED:
                updated.status = RunStatus.STARTING
        self.run_repository.save(updated)

    def _is_cancel_requested(self, run_id: UUID) -> bool:
        run = self.run_repository.get(run_id)
        return run is not None and run.status == RunStatus.CANCELLING

    @staticmethod
    def _keep_resources(payload: RunnerRunSpec) -> bool:
        metadata = payload.executor_config.get("metadata")
        if not isinstance(metadata, dict):
            return False
        keep_resources = metadata.get("keep_k8s_resources")
        return bool(keep_resources)

    @staticmethod
    def _local_artifact_dir(payload: RunnerRunSpec) -> Path:
        configured_root = payload.executor_config.get("artifact_path")
        if isinstance(configured_root, str) and configured_root.strip():
            base_dir = Path(configured_root).expanduser()
        else:
            base_dir = Path(
                tempfile.mkdtemp(prefix=f"agent-atlas-k8s-run-{str(payload.run_id)[:8]}-")
            )
        attempt_suffix = str(payload.attempt_id or payload.attempt)
        return base_dir / str(payload.run_id) / attempt_suffix / "artifacts"

    def _delete_job(self, request) -> None:
        self.client.delete_resource(
            kind="job",
            name=request.job_name,
            namespace=request.namespace,
        )


__all__ = [
    "K8sContainerRunner",
    "K8sJobSnapshot",
    "KubectlK8sClient",
]
