from __future__ import annotations

from typing import Protocol
from uuid import UUID

from agent_atlas_contracts.execution import ExecutionArtifact, ExecutionHandoff, RunnerRunSpec

from app.modules.runs.application.results import (
    PublishedRunExecutionResult,
    RunnerExecutionResult,
)
from app.modules.runs.domain.models import RunRecord, RunSpec, TrajectoryStep
from app.modules.shared.application.contracts import (
    RunObservationSinkPort as SharedRunObservationSinkPort,
)
from app.modules.shared.application.contracts import (
    TraceExportPort,
    TraceQueryPort,
)
from app.modules.shared.application.contracts import (
    TraceIngestionPort as SharedTraceIngestionPort,
)
from app.modules.shared.application.contracts import (
    TraceProjectorPort as SharedTraceProjectorPort,
)
from app.modules.shared.application.contracts import (
    TraceRepository as SharedTraceRepository,
)
from app.modules.shared.application.contracts import (
    TrajectoryStepProjectorPort as SharedTrajectoryStepProjectorPort,
)
from app.modules.shared.domain.traces import TraceSpan


class RunRepository(Protocol):
    def get(self, run_id: str | UUID) -> RunRecord | None: ...

    def list(self) -> list[RunRecord]: ...

    def save(self, run: RunRecord) -> None: ...


TraceBackendPort = TraceQueryPort
TraceExporterPort = TraceExportPort
TraceIngestionPort = SharedTraceIngestionPort
TraceProjectorPort = SharedTraceProjectorPort


class TraceRepository(SharedTraceRepository, Protocol):
    def list_for_run(self, run_id: str | UUID) -> list[TraceSpan]: ...


class TrajectoryRepository(Protocol):
    def list_for_run(self, run_id: str | UUID) -> list[TrajectoryStep]: ...

    def append(self, step: TrajectoryStep) -> None: ...


TrajectoryStepProjectorPort = SharedTrajectoryStepProjectorPort
RunObservationSinkPort = SharedRunObservationSinkPort


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
