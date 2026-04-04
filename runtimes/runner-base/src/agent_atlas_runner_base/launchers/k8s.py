from __future__ import annotations

from pathlib import PurePosixPath
from typing import Any
from uuid import UUID

from agent_atlas_contracts.execution import (
    RUNNER_CALLBACK_MODE_ENV,
    RUNNER_CALLBACK_MODE_STDOUT_JSONL,
    RunnerRunSpec,
)
from pydantic import BaseModel, Field

from agent_atlas_runner_base.claude_code import claude_code_k8s_command
from agent_atlas_runner_base.execution_profile import (
    execution_plane_config,
    execution_plane_value,
    runner_image,
)


class K8sJobLaunchRequest(BaseModel):
    job_name: str
    namespace: str
    config_map_name: str
    image: str
    command: list[str] = Field(default_factory=list)
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)
    config_map_manifest: dict[str, Any]
    job_manifest: dict[str, Any]


class K8sLauncher:
    def __init__(
        self,
        *,
        namespace: str = "agent-atlas-runs",
        service_account_name: str = "agent-atlas-runner",
    ) -> None:
        self.namespace = namespace
        self.service_account_name = service_account_name

    def build_request(self, payload: RunnerRunSpec) -> K8sJobLaunchRequest:
        job_name = self.job_name(payload)
        config_map_name = f"{job_name}-input"
        image = self._image_for_payload(payload)
        env = payload.bootstrap.as_environment()
        env[RUNNER_CALLBACK_MODE_ENV] = RUNNER_CALLBACK_MODE_STDOUT_JSONL
        args = payload.bootstrap.as_entrypoint_args()
        output_root = self._common_parent(
            payload.bootstrap.events_path,
            payload.bootstrap.runtime_result_path,
            payload.bootstrap.terminal_result_path,
            payload.bootstrap.artifact_manifest_path,
            payload.bootstrap.artifact_dir,
        )
        command = self._command(payload)
        container_spec: dict[str, Any] = {
            "name": "runner",
            "image": image,
            "command": command if command else None,
            "args": args,
            "env": [{"name": key, "value": value} for key, value in env.items()],
            "volumeMounts": [
                {
                    "name": "runner-input",
                    "mountPath": payload.bootstrap.run_spec_path,
                    "subPath": PurePosixPath(payload.bootstrap.run_spec_path).name,
                    "readOnly": True,
                },
                {
                    "name": "runner-output",
                    "mountPath": output_root,
                },
            ],
            "resources": self._resources(payload),
        }
        if container_spec["command"] is None:
            container_spec.pop("command")
        if container_spec["resources"] is None:
            container_spec.pop("resources")

        job_manifest = {
            "apiVersion": "batch/v1",
            "kind": "Job",
            "metadata": {
                "name": job_name,
                "namespace": self.namespace,
                "labels": self._labels(payload),
            },
            "spec": {
                "backoffLimit": 0,
                "template": {
                    "metadata": {
                        "labels": self._labels(payload),
                    },
                    "spec": {
                        "restartPolicy": "Never",
                        "serviceAccountName": self.service_account_name,
                        "containers": [container_spec],
                        "volumes": [
                            {
                                "name": "runner-input",
                                "configMap": {"name": config_map_name},
                            },
                            {
                                "name": "runner-output",
                                "emptyDir": {},
                            },
                        ],
                    },
                },
            },
        }
        timeout_seconds = execution_plane_value(payload.executor_config, "timeout_seconds")
        if isinstance(timeout_seconds, int) and timeout_seconds > 0:
            job_manifest["spec"]["activeDeadlineSeconds"] = timeout_seconds

        return K8sJobLaunchRequest(
            job_name=job_name,
            namespace=self.namespace,
            config_map_name=config_map_name,
            image=image,
            command=command,
            args=args,
            env=env,
            config_map_manifest={
                "apiVersion": "v1",
                "kind": "ConfigMap",
                "metadata": {
                    "name": config_map_name,
                    "namespace": self.namespace,
                    "labels": self._labels(payload),
                },
                "data": {
                    PurePosixPath(payload.bootstrap.run_spec_path).name: payload.model_dump_json(
                        indent=2
                    )
                },
            },
            job_manifest=job_manifest,
        )

    @staticmethod
    def job_name(payload: RunnerRunSpec) -> str:
        return K8sLauncher.job_name_for_ids(
            run_id=payload.run_id,
            attempt=payload.attempt,
            attempt_id=payload.attempt_id,
        )

    @staticmethod
    def job_name_for_ids(
        *,
        run_id: UUID,
        attempt: int = 1,
        attempt_id: UUID | None = None,
    ) -> str:
        run_prefix = str(run_id).replace("-", "")[:12]
        attempt_suffix = (
            str(attempt_id).replace("-", "")[:8] if attempt_id is not None else str(attempt)
        )
        return f"atlas-run-{run_prefix}-{attempt_suffix}".lower()

    @staticmethod
    def _labels(payload: RunnerRunSpec) -> dict[str, str]:
        labels = {
            "app.kubernetes.io/name": "agent-atlas-runner",
            "atlas.run_id": str(payload.run_id),
            "atlas.agent_type": payload.agent_type,
        }
        if payload.experiment_id is not None:
            labels["atlas.experiment_id"] = str(payload.experiment_id)
        return labels

    @staticmethod
    def _image_for_payload(payload: RunnerRunSpec) -> str:
        configured_runner_image = runner_image(payload.executor_config)
        if configured_runner_image is not None:
            return configured_runner_image
        raise ValueError("kubernetes runner requires execution binding runner_image")

    @staticmethod
    def _command(payload: RunnerRunSpec) -> list[str]:
        claude_code_command = claude_code_k8s_command(payload.executor_config)
        if claude_code_command is not None:
            return claude_code_command
        raw_command = execution_plane_config(payload.executor_config).get("command")
        if isinstance(raw_command, list) and all(isinstance(item, str) for item in raw_command):
            return raw_command
        return []

    @staticmethod
    def _resources(payload: RunnerRunSpec) -> dict[str, Any] | None:
        resources = execution_plane_value(payload.executor_config, "resources")
        if not isinstance(resources, dict):
            return None

        requests: dict[str, str] = {}
        limits: dict[str, str] = {}
        cpu = resources.get("cpu")
        memory = resources.get("memory")
        if isinstance(cpu, str) and cpu.strip():
            requests["cpu"] = cpu
            limits["cpu"] = cpu
        if isinstance(memory, str) and memory.strip():
            requests["memory"] = memory
            limits["memory"] = memory
        if not requests and not limits:
            return None
        return {"requests": requests, "limits": limits}

    @staticmethod
    def _common_parent(*paths: str) -> str:
        normalized = [PurePosixPath(path) for path in paths]
        first_parts = normalized[0].parts
        common_parts: list[str] = []
        for index, part in enumerate(first_parts):
            if all(
                len(candidate.parts) > index and candidate.parts[index] == part
                for candidate in normalized[1:]
            ):
                common_parts.append(part)
            else:
                break
        return str(PurePosixPath(*common_parts)) if common_parts else "/workspace/output"
