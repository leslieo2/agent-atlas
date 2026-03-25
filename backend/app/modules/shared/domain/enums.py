from __future__ import annotations

from enum import Enum


class RunStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    TERMINATED = "terminated"


class StepType(str, Enum):
    LLM = "llm"
    TOOL = "tool"
    PLANNER = "planner"
    MEMORY = "memory"


class EvalStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class ArtifactFormat(str, Enum):
    JSONL = "jsonl"
    PARQUET = "parquet"


class AdapterKind(str, Enum):
    OPENAI_AGENTS = "openai-agents-sdk"
    LANGCHAIN = "langchain"
    MCP = "mcp"
