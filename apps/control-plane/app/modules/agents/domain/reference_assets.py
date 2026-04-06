from __future__ import annotations

import json
import subprocess  # nosec - docker CLI invocation is an explicit starter bootstrap dependency
from pathlib import Path
from typing import Any

from app.core.errors import AgentBootstrapFailedError
from app.modules.agents.domain.constants import (
    CLAUDE_CODE_CLI_FRAMEWORK,
    CLAUDE_CODE_STARTER_TAGS,
)
from app.modules.agents.domain.models import AgentManifest
from app.modules.shared.domain.constants import EXTERNAL_RUNNER_EXECUTION_BACKEND
from app.modules.shared.domain.enums import AgentFamily
from app.modules.shared.domain.models import ExecutionBinding, ExecutorConfig

CLAUDE_CODE_STARTER_AGENT_ID = "claude-code-starter"
CLAUDE_CODE_STARTER_ENTRYPOINT = (
    "app.modules.agents.domain.reference_assets:build_claude_code_starter"
)
CLAUDE_CODE_STARTER_RUNNER_IMAGE = "atlas-claude-validation:local"
CLAUDE_CODE_STARTER_PROJECT_BUNDLE_ARTIFACT_REF = (
    "file:///opt/atlas-validation/project-bundle.tar.gz"
)
CLAUDE_CODE_STARTER_PROJECT_MOUNT_PATH = "/workspace/project"
CLAUDE_CODE_STARTER_FALLBACK_MODEL = "gpt-5.4-mini"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[6]


def _claude_code_settings_path() -> Path:
    return Path.home() / ".claude" / "settings.json"


def _claude_code_settings_default_model() -> str | None:
    settings_path = _claude_code_settings_path()
    if not settings_path.exists():
        return None
    try:
        raw_settings = json.loads(settings_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(raw_settings, dict):
        return None

    configured = raw_settings.get("ANTHROPIC_DEFAULT_OPUS_MODEL")
    if isinstance(configured, str) and configured.strip():
        return configured.strip()

    raw_env = raw_settings.get("env")
    if not isinstance(raw_env, dict):
        return None
    nested = raw_env.get("ANTHROPIC_DEFAULT_OPUS_MODEL")
    if isinstance(nested, str) and nested.strip():
        return nested.strip()
    return None


def _claude_code_starter_default_model() -> str:
    configured = _claude_code_settings_default_model()
    return configured or CLAUDE_CODE_STARTER_FALLBACK_MODEL


def provision_claude_code_starter_carrier(*, repo_root: Path | None = None) -> None:
    resolved_repo_root = (repo_root or _repo_root()).resolve()
    validation_root = resolved_repo_root / "runtimes" / "runner-base" / "validation"
    dockerfile = validation_root / "Dockerfile"
    if not dockerfile.exists():
        raise AgentBootstrapFailedError(
            "starter carrier bootstrap is unavailable because the validation Dockerfile is missing",
            agent_id=CLAUDE_CODE_STARTER_AGENT_ID,
        )

    inspect = subprocess.run(  # nosec - controlled local docker inspect/build path for starter bootstrap
        ["docker", "image", "inspect", CLAUDE_CODE_STARTER_RUNNER_IMAGE],
        cwd=resolved_repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if inspect.returncode == 0:
        return

    build = subprocess.run(  # nosec - controlled local docker inspect/build path for starter bootstrap
        [
            "docker",
            "build",
            "-f",
            str(dockerfile),
            "-t",
            CLAUDE_CODE_STARTER_RUNNER_IMAGE,
            ".",
        ],
        cwd=resolved_repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if build.returncode == 0:
        return

    detail = build.stderr.strip() or inspect.stderr.strip() or "docker build failed"
    raise AgentBootstrapFailedError(
        f"failed to provision starter carrier image '{CLAUDE_CODE_STARTER_RUNNER_IMAGE}': {detail}",
        agent_id=CLAUDE_CODE_STARTER_AGENT_ID,
    )


def claude_code_starter_manifest() -> AgentManifest:
    return AgentManifest(
        agent_id=CLAUDE_CODE_STARTER_AGENT_ID,
        name="Claude Code Starter",
        description="Starter agent template for live code-edit validation and experiment flows.",
        agent_family=AgentFamily.CLAUDE_CODE.value,
        framework=CLAUDE_CODE_CLI_FRAMEWORK,
        default_model=_claude_code_starter_default_model(),
        tags=list(CLAUDE_CODE_STARTER_TAGS),
    )


def build_claude_code_starter() -> AgentManifest:
    return claude_code_starter_manifest().model_copy(deep=True)


def claude_code_starter_runtime_profile() -> ExecutorConfig:
    return ExecutorConfig(backend=EXTERNAL_RUNNER_EXECUTION_BACKEND)


def claude_code_starter_execution_binding() -> ExecutionBinding:
    return ExecutionBinding(
        runner_backend="docker-container",
        runner_image=CLAUDE_CODE_STARTER_RUNNER_IMAGE,
        config={
            "project_materialization": {
                "mode": "artifact_bundle",
                "artifact_ref": CLAUDE_CODE_STARTER_PROJECT_BUNDLE_ARTIFACT_REF,
                "mount_path": CLAUDE_CODE_STARTER_PROJECT_MOUNT_PATH,
            },
            "claude_code_cli": {
                "command": "claude",
                "args": ["--dangerously-skip-permissions"],
                "version": "starter",
            },
        },
    )


def _starter_cli_config(binding: ExecutionBinding | None) -> dict[str, Any]:
    if binding is None or not isinstance(binding.config, dict):
        return {}
    cli_config = binding.config.get("claude_code_cli")
    if not isinstance(cli_config, dict):
        return {}
    return cli_config


def is_claude_code_starter_execution_binding(binding: ExecutionBinding | None) -> bool:
    if binding is None:
        return False
    runner_backend = str(binding.runner_backend).strip().lower()
    if runner_backend != "docker-container":
        return False
    if binding.runner_image != CLAUDE_CODE_STARTER_RUNNER_IMAGE:
        return False
    return _starter_cli_config(binding).get("version") == "starter"


def ensure_claude_code_starter_runtime_ready(
    binding: ExecutionBinding | None = None,
) -> None:
    resolved_binding = binding or claude_code_starter_execution_binding()
    if not is_claude_code_starter_execution_binding(resolved_binding):
        return
    provision_claude_code_starter_carrier()
