from __future__ import annotations

from typing import Protocol
from uuid import UUID

from agent_atlas_contracts.execution import ExecutionArtifact, ExecutionHandoff, RunnerRunSpec

from app.modules.shared.application.contracts import (
    RunObservationSinkPort,
    RunRepository,
    TraceExportPort,
    TraceIngestionPort,
    TraceProjectorPort,
    TraceQueryPort,
    TraceRepository,
    TrajectoryRepository,
    TrajectoryStepProjectorPort,
)
from app.modules.runs.application.results import (
    PublishedRunExecutionResult,
    RunnerExecutionResult,
)
from app.modules.runs.domain.models import RunSpec


TraceBackendPort = TraceQueryPort
TraceExporterPort = TraceExportPort


class PublishedRunRuntimePort(Protocol):
    def execute_published(
        self,
        run_id: UUID,
        payload: RunnerRunSpec,
    ) -> PublishedRunExecutionResult: ...


class ArtifactResolverPort(Protocol):
    def resolve(self, payload: RunSpec) -> ExecutionArtifact: ...


class RunnerPort(Protocol):
    def execute(self, handoff: ExecutionHandoff) -> RunnerExecutionResult: ...
