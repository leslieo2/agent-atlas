from __future__ import annotations

from uuid import uuid4

from agent_atlas_contracts.execution import ExecutionArtifact, RunnerBootstrapPaths
from agent_atlas_contracts.runtime import (
    event_envelope_to_trace_event,
    producer_for_runtime,
    trace_event_to_event_envelope,
)
from app.execution.adapters import runner_run_spec_from_run_spec
from app.execution.application.results import (
    PublishedRunExecutionResult,
    RuntimeExecutionResult,
)
from app.execution.contracts import ExecutionRunSpec
from app.modules.shared.domain.enums import AdapterKind, StepType
from app.modules.shared.domain.models import ProvenanceMetadata
from app.modules.shared.domain.traces import TraceIngestEvent


def test_runner_bootstrap_paths_render_env_and_args():
    paths = RunnerBootstrapPaths()

    env = paths.as_environment()
    args = paths.as_entrypoint_args()

    assert env["ATLAS_RUNSPEC_PATH"].endswith("run_spec.json")
    assert env["ATLAS_EVENTS_PATH"].endswith("events.ndjson")
    assert env["ATLAS_RUNTIME_RESULT_PATH"].endswith("runtime_result.json")
    assert "--run-spec" in args
    assert "--runtime-result" in args
    assert "--artifact-dir" in args


def test_runner_run_spec_can_be_built_from_execution_run_spec():
    run_id = uuid4()
    payload = ExecutionRunSpec(
        run_id=run_id,
        experiment_id=uuid4(),
        project="atlas",
        dataset="ops",
        agent_id="triage-bot",
        model="gpt-5.4-mini",
        entrypoint="app.modules.agents.fixtures.basic:build_agent",
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
                "entrypoint": "app.modules.agents.fixtures.basic:build_agent",
                "source_fingerprint": "fingerprint",
                "execution_reference": {
                    "artifact_ref": "source://triage-bot@fingerprint",
                    "image_ref": None,
                },
                "default_runtime_profile": {"backend": "k8s-job"},
            },
            artifact_ref="source://triage-bot@fingerprint",
        ),
    )

    runner_spec = runner_run_spec_from_run_spec(
        payload,
        artifact=ExecutionArtifact(
            framework=AdapterKind.OPENAI_AGENTS.value,
            entrypoint="app.modules.agents.fixtures.basic:build_agent",
            source_fingerprint="fingerprint",
            artifact_ref="source://triage-bot@fingerprint",
            image_ref=None,
            published_agent_snapshot=payload.provenance.published_agent_snapshot or {},
        ),
        runner_backend="local-process",
        attempt=2,
    )

    assert runner_spec.run_id == run_id
    assert runner_spec.attempt == 2
    assert runner_spec.agent_type == AdapterKind.OPENAI_AGENTS.value
    assert runner_spec.published_agent_snapshot["manifest"]["agent_id"] == "triage-bot"
    assert runner_spec.tracing is not None
    assert runner_spec.tracing.export is not None
    serialized = runner_spec.model_dump(mode="json")
    assert "input_summary" not in serialized
    assert "approval_policy" not in serialized


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
