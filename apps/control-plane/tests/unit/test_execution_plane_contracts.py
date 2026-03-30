from __future__ import annotations

from uuid import uuid4

from agent_atlas_contracts.execution import RunnerBootstrapPaths
from app.execution_plane.specs import runner_run_spec_from_run_spec
from app.modules.runs.application.results import PublishedRunExecutionResult
from app.modules.runs.application.runtime_translation import (
    event_envelope_to_trace_event,
    producer_for_runtime,
    trace_event_to_event_envelope,
)
from app.modules.runs.domain.models import RunSpec, RuntimeExecutionResult
from app.modules.shared.domain.enums import AdapterKind, StepType
from app.modules.shared.domain.models import ProvenanceMetadata
from app.modules.shared.domain.traces import TraceIngestEvent


def test_runner_bootstrap_paths_render_env_and_args():
    paths = RunnerBootstrapPaths()

    env = paths.as_environment()
    args = paths.as_entrypoint_args()

    assert env["ATLAS_RUNSPEC_PATH"].endswith("run_spec.json")
    assert env["ATLAS_EVENTS_PATH"].endswith("events.ndjson")
    assert "--run-spec" in args
    assert "--artifact-dir" in args


def test_runner_run_spec_can_be_built_from_legacy_run_spec():
    run_id = uuid4()
    payload = RunSpec(
        run_id=run_id,
        experiment_id=uuid4(),
        project="atlas",
        dataset="ops",
        agent_id="triage-bot",
        model="gpt-5.4-mini",
        entrypoint="app.agent_plugins.basic:build_agent",
        agent_type=AdapterKind.OPENAI_AGENTS,
        input_summary="check ticket",
        prompt="Summarize the incident.",
        provenance=ProvenanceMetadata(
            framework=AdapterKind.OPENAI_AGENTS.value,
            published_agent_snapshot={
                "manifest": {
                    "agent_id": "triage-bot",
                    "name": "Triage Bot",
                    "description": "Checks incidents",
                    "framework": AdapterKind.OPENAI_AGENTS.value,
                    "default_model": "gpt-5.4-mini",
                    "tags": [],
                },
                "entrypoint": "app.agent_plugins.basic:build_agent",
            },
            artifact_ref="source://triage-bot@fingerprint",
        ),
    )

    runner_spec = runner_run_spec_from_run_spec(payload, attempt=2)

    assert runner_spec.run_id == run_id
    assert runner_spec.attempt == 2
    assert runner_spec.agent_type == AdapterKind.OPENAI_AGENTS.value
    assert runner_spec.published_agent_snapshot["manifest"]["agent_id"] == "triage-bot"
    assert runner_spec.tracing is not None
    assert runner_spec.tracing.export is not None


def test_event_envelope_round_trips_to_trace_event():
    run_id = uuid4()
    trace_event = TraceIngestEvent(
        run_id=run_id,
        span_id=f"span-{run_id}-1",
        step_type=StepType.TOOL,
        name="lookup_order_status",
        input={"prompt": '{"order_id":"ORD-1"}'},
        output={"output": "delivered", "success": True},
        tool_name="lookup_order_status",
        latency_ms=11,
        token_usage=4,
    )

    envelope = trace_event_to_event_envelope(
        trace_event,
        experiment_id=None,
        attempt=1,
        attempt_id=None,
        producer=producer_for_runtime(runtime="openai-agents-sdk"),
        sequence=1,
    )
    restored = event_envelope_to_trace_event(envelope)

    assert envelope.event_type == "tool.succeeded"
    assert restored is not None
    assert restored.step_type == StepType.TOOL
    assert restored.tool_name == "lookup_order_status"


def test_published_run_execution_result_projects_trace_events_from_event_envelopes():
    run_id = uuid4()
    trace_event = TraceIngestEvent(
        run_id=run_id,
        span_id=f"span-{run_id}-1",
        step_type=StepType.LLM,
        name="gpt-5.4-mini",
        input={"prompt": "Explain the plan."},
        output={"output": "Here is the plan.", "success": True},
    )
    result = PublishedRunExecutionResult(
        runtime_result=RuntimeExecutionResult(
            output="Here is the plan.",
            latency_ms=8,
            token_usage=12,
            provider="mock",
        ),
        event_envelopes=[
            trace_event_to_event_envelope(
                trace_event,
                experiment_id=None,
                attempt=1,
                attempt_id=None,
                producer=producer_for_runtime(runtime="mock"),
                sequence=1,
            )
        ],
    )

    projected = result.projected_trace_events()

    assert len(projected) == 1
    assert projected[0].span_id == f"span-{run_id}-1"
    assert projected[0].step_type == StepType.LLM
