from __future__ import annotations

from app.modules.shared.domain.enums import AgentFamily

CLAUDE_CODE_CLI_FRAMEWORK = "claude-code-cli"
STARTER_AGENT_TAG = "starter"
LIVE_BOOTSTRAP_TAG = "live-bootstrap"
CLAUDE_CODE_STARTER_TAGS = (
    STARTER_AGENT_TAG,
    AgentFamily.CLAUDE_CODE.value,
    LIVE_BOOTSTRAP_TAG,
)
