from __future__ import annotations

import subprocess
from pathlib import Path

from app.core.config import RuntimeMode, settings
from app.core.errors import AgentBootstrapFailedError
from app.modules.agents.domain.constants import (
    CLAUDE_CODE_CLI_FRAMEWORK,
    CLAUDE_CODE_STARTER_TAGS,
)
from app.modules.agents.domain.models import AgentManifest
from app.modules.shared.domain.constants import EXTERNAL_RUNNER_EXECUTION_BACKEND
from app.modules.shared.domain.enums import AgentFamily
from app.modules.shared.domain.models import ExecutorConfig

CLAUDE_CODE_STARTER_AGENT_ID = "claude-code-starter"
CLAUDE_CODE_STARTER_ENTRYPOINT = (
    "app.modules.agents.domain.starter_assets:build_claude_code_starter"
)
CLAUDE_CODE_STARTER_RUNNER_IMAGE = "atlas-claude-validation:local"
CLAUDE_CODE_STARTER_SYSTEM_PROMPT = (
    "Reply with the user prompt text only. No greeting or explanation."
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[6]


def provision_claude_code_starter_carrier(*, repo_root: Path | None = None) -> None:
    resolved_repo_root = (repo_root or _repo_root()).resolve()
    validation_root = resolved_repo_root / "runtimes" / "runner-base" / "validation"
    dockerfile = validation_root / "Dockerfile"
    if not dockerfile.exists():
        raise AgentBootstrapFailedError(
            "starter carrier bootstrap is unavailable because the validation Dockerfile is missing",
            agent_id=CLAUDE_CODE_STARTER_AGENT_ID,
        )

    inspect = subprocess.run(  # nosec B603
        ["docker", "image", "inspect", CLAUDE_CODE_STARTER_RUNNER_IMAGE],
        cwd=resolved_repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if inspect.returncode == 0:
        return

    build = subprocess.run(  # nosec B603
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
        description="Starter agent template for live-mode Atlas validation and experiment flows.",
        agent_family=AgentFamily.CLAUDE_CODE.value,
        framework=CLAUDE_CODE_CLI_FRAMEWORK,
        default_model="gpt-5.4-mini",
        tags=list(CLAUDE_CODE_STARTER_TAGS),
    )


def build_claude_code_starter() -> AgentManifest:
    return claude_code_starter_manifest().model_copy(deep=True)


def claude_code_starter_runtime_profile() -> ExecutorConfig:
    return ExecutorConfig(
        backend=EXTERNAL_RUNNER_EXECUTION_BACKEND,
        runner_image=CLAUDE_CODE_STARTER_RUNNER_IMAGE,
        metadata={
            "runner_backend": "docker-container",
            "claude_code_cli": {
                "command": "claude",
                "args": ["--dangerously-skip-permissions"],
                "system_prompt": CLAUDE_CODE_STARTER_SYSTEM_PROMPT,
                "version": "starter",
            },
        },
    )


def ensure_claude_code_starter_runtime_ready() -> None:
    if settings.effective_runtime_mode() != RuntimeMode.LIVE:
        return
    runtime_profile = claude_code_starter_runtime_profile()
    runner_backend = str(runtime_profile.metadata.get("runner_backend", "")).strip().lower()
    if runner_backend != "docker-container":
        return
    provision_claude_code_starter_carrier()
