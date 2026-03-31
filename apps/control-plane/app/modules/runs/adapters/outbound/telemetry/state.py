from __future__ import annotations

from uuid import UUID

from app.modules.runs.application.ports import RunRepository
from app.modules.runs.domain.policies import RunAggregate
from app.modules.shared.application.contracts import RunTracingStatePort
from app.modules.shared.domain.models import TracePointer, TracingMetadata


class RunTracingStateRecorder(RunTracingStatePort):
    def __init__(self, run_repository: RunRepository) -> None:
        self.run_repository = run_repository

    def record_tracing(
        self,
        run_id: str | UUID,
        tracing: TracingMetadata,
    ) -> None:
        run = self.run_repository.get(run_id)
        if not run:
            return
        updated = RunAggregate.load(run)
        updated.run.tracing = tracing
        updated.run.trace_pointer = TracePointer(
            backend=tracing.backend,
            trace_id=tracing.trace_id,
            trace_url=tracing.trace_url,
            project_url=tracing.project_url,
        )
        if updated.run.provenance is not None:
            updated.run.provenance.trace_backend = tracing.backend
        self.run_repository.save(updated.run)


__all__ = ["RunTracingStateRecorder"]
