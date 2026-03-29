from __future__ import annotations

from dataclasses import dataclass

from app.bootstrap.wiring.infrastructure import InfrastructureBundle
from app.modules.traces.application.use_cases import (
    TraceCommands,
    TraceIngestionWorkflow,
)


@dataclass(frozen=True)
class TraceModuleBundle:
    trace_workflow: TraceIngestionWorkflow
    trace_commands: TraceCommands


def build_trace_module(infra: InfrastructureBundle) -> TraceModuleBundle:
    trace_workflow = TraceIngestionWorkflow(
        trace_projector=infra.trace_projector,
    )
    trace_commands = TraceCommands(workflow=trace_workflow)

    return TraceModuleBundle(
        trace_workflow=trace_workflow,
        trace_commands=trace_commands,
    )
