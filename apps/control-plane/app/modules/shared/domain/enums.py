from __future__ import annotations

from enum import Enum


class RunStatus(str, Enum):
    QUEUED = "queued"
    STARTING = "starting"
    RUNNING = "running"
    CANCELLING = "cancelling"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    LOST = "lost"


class StepType(str, Enum):
    LLM = "llm"
    TOOL = "tool"
    PLANNER = "planner"
    MEMORY = "memory"


class ArtifactFormat(str, Enum):
    JSONL = "jsonl"
    PARQUET = "parquet"


class AdapterKind(str, Enum):
    OPENAI_AGENTS = "openai-agents-sdk"
    LANGCHAIN = "langchain"
    MCP = "mcp"


class AgentFamily(str, Enum):
    OPENAI_AGENTS = "openai-agents"
    LANGCHAIN = "langchain"
    MCP = "mcp"
    CLAUDE_CODE = "claude-code"


class ScoringMode(str, Enum):
    EXACT_MATCH = "exact_match"
    CONTAINS = "contains"


class SampleJudgement(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    UNSCORED = "unscored"
    RUNTIME_ERROR = "runtime_error"


class CurationStatus(str, Enum):
    INCLUDE = "include"
    EXCLUDE = "exclude"
    REVIEW = "review"


class CompareOutcome(str, Enum):
    IMPROVED = "improved"
    REGRESSED = "regressed"
    UNCHANGED_PASS = "unchanged_pass"  # nosec B105 - compare label, not a credential
    UNCHANGED_FAIL = "unchanged_fail"
    CANDIDATE_ONLY = "candidate_only"
    BASELINE_ONLY = "baseline_only"


class PolicyEffect(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
