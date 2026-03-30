from __future__ import annotations

from typing import Protocol
from uuid import UUID

from agent_atlas_contracts.execution import ExecutionArtifact, ExecutionHandoff, RunnerRunSpec

from app.agent_tracing.ports import TraceExportPort, TraceQueryPort
from app.modules.runs.application.results import (
    PublishedRunExecutionResult,
    RunnerExecutionResult,
)
from app.modules.runs.domain.models import (
    RunRecord,
    RunSpec,
    TrajectoryStep,
)
from app.modules.shared.domain.traces import TraceIngestEvent, TraceSpan


class RunRepository(Protocol):
    def get(self, run_id: str | UUID) -> RunRecord | None: ...

    def list(self) -> list[RunRecord]: ...

    def save(self, run: RunRecord) -> None: ...


class TrajectoryRepository(Protocol):
    def list_for_run(self, run_id: str | UUID) -> list[TrajectoryStep]: ...

    def append(self, step: TrajectoryStep) -> None: ...


class TraceRepository(Protocol):
    def list_for_run(self, run_id: str | UUID) -> list[TraceSpan]: ...

    def append(self, span: TraceSpan) -> None: ...


class TrajectoryStepProjectorPort(Protocol):
    def project(
        self,
        event: TraceIngestEvent,
        span: TraceSpan | None = None,
    ) -> TrajectoryStep: ...


TraceBackendPort = TraceQueryPort
TraceExporterPort = TraceExportPort


class TraceProjectorPort(Protocol):
    def project(self, event: TraceIngestEvent) -> TraceSpan: ...

    def normalize(
        self,
        span: TraceSpan,
        event: TraceIngestEvent | None = None,
    ) -> dict[str, object]: ...


class PublishedRunRuntimePort(Protocol):
    def execute_published(
        self,
        run_id: UUID,
        payload: RunnerRunSpec,
    ) -> PublishedRunExecutionResult: ...


class TraceIngestionPort(Protocol):
    def ingest(self, event: TraceIngestEvent) -> TraceSpan: ...


class ArtifactResolverPort(Protocol):
    def resolve(self, payload: RunSpec) -> ExecutionArtifact: ...


class RunnerPort(Protocol):
    def execute(self, handoff: ExecutionHandoff) -> RunnerExecutionResult: ...
