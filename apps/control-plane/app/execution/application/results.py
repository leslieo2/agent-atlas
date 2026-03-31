from __future__ import annotations

from dataclasses import dataclass

from agent_atlas_contracts.runtime import PublishedRunExecutionResult, RuntimeExecutionResult


@dataclass(frozen=True)
class ExecutionMetrics:
    latency_ms: int = 0
    token_cost: int = 0
    tool_calls: int = 0


@dataclass(frozen=True)
class RunnerExecutionResult:
    runner_backend: str
    artifact_ref: str | None
    image_ref: str | None
    execution: PublishedRunExecutionResult


__all__ = [
    "ExecutionMetrics",
    "PublishedRunExecutionResult",
    "RunnerExecutionResult",
    "RuntimeExecutionResult",
]
