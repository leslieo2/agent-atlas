from __future__ import annotations

from dataclasses import dataclass

from agent_atlas_contracts.runtime import (
    PublishedRunExecutionResult,
    RuntimeExecutionResult,
    TraceIngestEvent,
)


class ExecutionCancelled(Exception):
    pass


@dataclass(frozen=True)
class ExecutionMetrics:
    latency_ms: int = 0
    token_cost: int = 0
    tool_calls: int = 0


@dataclass(frozen=True)
class ProjectedExecutionRecord:
    events: list[TraceIngestEvent]
    metrics: ExecutionMetrics


@dataclass(frozen=True)
class RunFailureDetails:
    code: str
    message: str


@dataclass(frozen=True)
class RunnerSubmissionRecord:
    runner_backend: str
    framework_type: str | None = None
    framework: str | None = None
    artifact_ref: str | None = None
    image_ref: str | None = None


@dataclass(frozen=True)
class RunnerExecutionResult:
    runner_backend: str
    artifact_ref: str | None
    image_ref: str | None
    execution: PublishedRunExecutionResult


__all__ = [
    "ExecutionCancelled",
    "ExecutionMetrics",
    "ProjectedExecutionRecord",
    "PublishedRunExecutionResult",
    "RunFailureDetails",
    "RunnerExecutionResult",
    "RunnerSubmissionRecord",
    "RuntimeExecutionResult",
]
