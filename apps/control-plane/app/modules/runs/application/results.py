from __future__ import annotations

from dataclasses import dataclass

from agent_atlas_contracts.runtime import PublishedRunExecutionResult


@dataclass(frozen=True)
class RunnerExecutionResult:
    runner_backend: str
    artifact_ref: str | None
    image_ref: str | None
    execution: PublishedRunExecutionResult
