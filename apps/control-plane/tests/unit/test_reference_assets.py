from __future__ import annotations

from pathlib import Path

import pytest
from app.core.errors import AgentBootstrapFailedError
from app.modules.agents.domain.reference_assets import (
    CLAUDE_CODE_STARTER_AGENT_ID,
    CLAUDE_CODE_STARTER_ENTRYPOINT,
    CLAUDE_CODE_STARTER_PROJECT_BUNDLE_ARTIFACT_REF,
    CLAUDE_CODE_STARTER_PROJECT_MOUNT_PATH,
    CLAUDE_CODE_STARTER_RUNNER_IMAGE,
    claude_code_starter_execution_binding,
    claude_code_starter_manifest,
    claude_code_starter_runtime_profile,
    ensure_claude_code_starter_runtime_ready,
    is_claude_code_starter_execution_binding,
    provision_claude_code_starter_carrier,
)
from app.modules.shared.domain.models import ExecutionBinding


def _write_validation_dockerfile(repo_root: Path) -> None:
    dockerfile = repo_root / "runtimes" / "runner-base" / "validation" / "Dockerfile"
    dockerfile.parent.mkdir(parents=True, exist_ok=True)
    dockerfile.write_text("FROM scratch\n", encoding="utf-8")


def test_provision_claude_code_starter_carrier_skips_build_when_image_exists(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _write_validation_dockerfile(tmp_path)
    commands: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        commands.append(list(cmd))
        return type("Completed", (), {"returncode": 0, "stderr": "", "stdout": ""})()

    monkeypatch.setattr("app.modules.agents.domain.reference_assets.subprocess.run", fake_run)

    provision_claude_code_starter_carrier(repo_root=tmp_path)

    assert commands == [["docker", "image", "inspect", CLAUDE_CODE_STARTER_RUNNER_IMAGE]]


def test_provision_claude_code_starter_carrier_builds_missing_image(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _write_validation_dockerfile(tmp_path)
    commands: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        commands.append(list(cmd))
        returncode = 1 if cmd[:3] == ["docker", "image", "inspect"] else 0
        return type("Completed", (), {"returncode": returncode, "stderr": "", "stdout": ""})()

    monkeypatch.setattr("app.modules.agents.domain.reference_assets.subprocess.run", fake_run)

    provision_claude_code_starter_carrier(repo_root=tmp_path)

    assert commands == [
        ["docker", "image", "inspect", CLAUDE_CODE_STARTER_RUNNER_IMAGE],
        [
            "docker",
            "build",
            "-f",
            str(tmp_path / "runtimes" / "runner-base" / "validation" / "Dockerfile"),
            "-t",
            CLAUDE_CODE_STARTER_RUNNER_IMAGE,
            ".",
        ],
    ]


def test_provision_claude_code_starter_carrier_raises_when_build_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _write_validation_dockerfile(tmp_path)

    def fake_run(cmd, **kwargs):
        if cmd[:3] == ["docker", "image", "inspect"]:
            return type("Completed", (), {"returncode": 1, "stderr": "missing", "stdout": ""})()
        return type("Completed", (), {"returncode": 1, "stderr": "build exploded", "stdout": ""})()

    monkeypatch.setattr("app.modules.agents.domain.reference_assets.subprocess.run", fake_run)

    with pytest.raises(
        AgentBootstrapFailedError,
        match="failed to provision starter carrier image",
    ):
        provision_claude_code_starter_carrier(repo_root=tmp_path)


def test_ensure_claude_code_starter_runtime_ready_provisions_for_docker_carrier(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    monkeypatch.setattr(
        "app.modules.agents.domain.reference_assets.provision_claude_code_starter_carrier",
        lambda: calls.append("called"),
    )

    ensure_claude_code_starter_runtime_ready()
    assert calls == ["called"]


def test_ensure_claude_code_starter_runtime_ready_skips_non_starter_binding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    monkeypatch.setattr(
        "app.modules.agents.domain.reference_assets.provision_claude_code_starter_carrier",
        lambda: calls.append("called"),
    )

    ensure_claude_code_starter_runtime_ready(ExecutionBinding(runner_backend="local-process"))
    assert calls == []


def test_is_claude_code_starter_execution_binding_matches_only_starter_contract() -> None:
    assert is_claude_code_starter_execution_binding(claude_code_starter_execution_binding()) is True
    assert (
        is_claude_code_starter_execution_binding(
            ExecutionBinding(
                runner_backend="docker-container",
                runner_image=CLAUDE_CODE_STARTER_RUNNER_IMAGE,
                config={"claude_code_cli": {"version": "not-starter"}},
            )
        )
        is False
    )


def test_starter_helpers_expose_only_bridge_defaults() -> None:
    manifest = claude_code_starter_manifest()
    binding = claude_code_starter_execution_binding()

    assert manifest.agent_id == CLAUDE_CODE_STARTER_AGENT_ID
    assert CLAUDE_CODE_STARTER_ENTRYPOINT
    assert claude_code_starter_runtime_profile().backend == "external-runner"
    assert binding.runner_backend == "docker-container"
    assert binding.config["project_materialization"] == {
        "mode": "artifact_bundle",
        "artifact_ref": CLAUDE_CODE_STARTER_PROJECT_BUNDLE_ARTIFACT_REF,
        "mount_path": CLAUDE_CODE_STARTER_PROJECT_MOUNT_PATH,
    }
    assert binding.config["claude_code_cli"] == {
        "command": "claude",
        "args": ["--dangerously-skip-permissions"],
        "version": "starter",
    }
