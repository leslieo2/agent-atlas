from __future__ import annotations

from app.modules.agents.domain.models import AgentManifest
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


def claude_code_starter_manifest() -> AgentManifest:
    return AgentManifest(
        agent_id=CLAUDE_CODE_STARTER_AGENT_ID,
        name="Claude Code Starter",
        description="Starter agent template for live-mode Atlas validation and experiment flows.",
        agent_family=AgentFamily.CLAUDE_CODE.value,
        framework="claude-code-cli",
        default_model="gpt-5.4-mini",
        tags=["starter", "claude-code", "live-bootstrap"],
    )


def build_claude_code_starter() -> AgentManifest:
    return claude_code_starter_manifest().model_copy(deep=True)


def claude_code_starter_runtime_profile() -> ExecutorConfig:
    return ExecutorConfig(
        backend="external-runner",
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
