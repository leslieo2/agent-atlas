from __future__ import annotations

from uuid import uuid4

from agent_atlas_contracts.execution import ExecutionArtifact
from agent_atlas_contracts.runtime import TraceTelemetryMetadata
from app.agent_tracing.adapters.trace_projector import TraceIngestProjector
from app.agent_tracing.application import (
    RunObservationService,
    RunTelemetryIngestionService,
    RunTraceMetadataRecorder,
    TraceExportCoordinator,
    TraceSpanRecorder,
    TrajectoryRecorder,
)
from app.core.errors import AgentFrameworkMismatchError, ProviderAuthError
from app.data_plane.adapters.trajectory_projector import TraceEventTrajectoryProjector
from app.execution.application import (
    ExecutionCancelled,
    ExecutionMetrics,
    ExecutionRecorder,
    ProjectedExecutionRecord,
    PublishedRunExecutionResult,
    RunExecutionContext,
    RunExecutionProjector,
    RunnerExecutionResult,
    RunnerSubmissionRecord,
    RuntimeExecutionResult,
)
from app.execution.contracts import ExecutionRunSpec
from app.infrastructure.repositories import (
    StateRunRepository,
    StateTraceRepository,
    StateTrajectoryRepository,
)
from app.modules.runs.adapters.outbound.execution.state_sink import RunExecutionStateSink
from app.modules.runs.adapters.outbound.telemetry import RunTracingStateRecorder
from app.modules.runs.domain.models import RunRecord
from app.modules.shared.domain.enums import AdapterKind, RunStatus, StepType
from app.modules.shared.domain.models import ExecutionBinding
from app.modules.shared.domain.models import ExecutionProfile as ExecutorConfig
from app.modules.shared.domain.traces import TraceIngestEvent
from tests.support.fake_phoenix import FakeOtlpTraceExporter


def _build_telemetry_ingestor(
    run_repository: StateRunRepository,
    trace_repository: StateTraceRepository,
    trajectory_repository: StateTrajectoryRepository,
) -> RunTelemetryIngestionService:
    return RunObservationService(
        trace_span_recorder=TraceSpanRecorder(
            trace_repository=trace_repository,
            trace_projector=TraceIngestProjector(),
        ),
        trajectory_recorder=TrajectoryRecorder(
            trajectory_repository=trajectory_repository,
            step_projector=TraceEventTrajectoryProjector(),
        ),
        trace_export_coordinator=TraceExportCoordinator(
            trace_exporter=FakeOtlpTraceExporter(
                endpoint="http://phoenix.test:6006/v1/traces",
                project_name="agent-atlas-tests",
                backend_name="phoenix",
                base_url="http://phoenix.test:6006",
            ),
            trace_metadata_recorder=RunTraceMetadataRecorder(
                run_tracing_state=RunTracingStateRecorder(
                    run_repository=run_repository,
                ),
            ),
        ),
    )


class _FixedArtifactResolver:
    def resolve(self, payload: ExecutionRunSpec) -> ExecutionArtifact:
        entrypoint = payload.entrypoint or "tests.fixtures.agents.basic:build_agent"
        return ExecutionArtifact(
            framework=payload.agent_type.value,
            entrypoint=entrypoint,
            source_fingerprint="fingerprint-test",
            artifact_ref=f"source://{payload.agent_id or 'basic'}@fingerprint-test",
            image_ref=None,
            published_agent_snapshot={
                "manifest": {
                    "agent_id": payload.agent_id or "basic",
                    "name": "Basic",
                    "description": "Basic agent",
                    "framework": payload.agent_type.value,
                    "default_model": payload.model,
                    "tags": [],
                },
                "entrypoint": entrypoint,
                "published_at": "2026-03-20T09:00:00Z",
            },
        )


def test_run_execution_projector_builds_success_trace_event():
    run_id = uuid4()
    context = RunExecutionContext.from_spec(
        run_id,
        ExecutionRunSpec(
            project="control-plane",
            dataset="crm-v2",
            model="gpt-5.4-mini",
            agent_type=AdapterKind.OPENAI_AGENTS,
            input_summary="projector test",
            prompt="Explain the plan.",
            project_metadata={"image_digest": "sha256:test", "prompt_version": "v2"},
        ),
    ).with_runner_submission(
        RunnerSubmissionRecord(
            runner_backend="local-process",
            framework=AdapterKind.OPENAI_AGENTS.value,
            artifact_ref="source://basic@fingerprint-test",
            image_ref="ghcr.io/example/basic:latest",
        )
    )
    projector = RunExecutionProjector()

    record = projector.project_runtime_success(
        context,
        PublishedRunExecutionResult(
            runtime_result=RuntimeExecutionResult(
                output="Projected success output",
                latency_ms=17,
                token_usage=31,
                provider="mock",
                execution_backend="local",
                container_image="python:3.12-slim",
            )
        ),
    )

    assert len(record.events) == 1
    assert record.events[0].span_id == f"span-{run_id}-1"
    assert record.events[0].parent_span_id is None
    assert record.events[0].output["output"] == "Projected success output"
    assert record.events[0].output["provider"] == "mock"
    assert record.events[0].image_digest == "python:3.12-slim"
    assert record.events[0].metadata is not None
    assert record.events[0].metadata.framework == AdapterKind.OPENAI_AGENTS.value
    assert record.events[0].metadata.artifact_ref == "source://basic@fingerprint-test"
    assert record.events[0].metadata.image_ref == "ghcr.io/example/basic:latest"
    assert record.events[0].metadata.runner_backend == "local-process"
    assert record.events[0].metadata.image_digest == "python:3.12-slim"
    assert record.events[0].metadata.prompt_version == "v2"
    assert record.metrics.token_cost == 31


def test_run_execution_projector_backfills_missing_runtime_event_metadata_from_runner_submission():
    run_id = uuid4()
    context = RunExecutionContext.from_spec(
        run_id,
        ExecutionRunSpec(
            project="control-plane",
            dataset="crm-v2",
            agent_id="basic",
            model="gpt-5.4-mini",
            agent_type=AdapterKind.OPENAI_AGENTS,
            input_summary="projector metadata backfill",
            prompt="Explain the plan.",
        ),
    ).with_runner_submission(
        RunnerSubmissionRecord(
            runner_backend="local-process",
            framework=AdapterKind.OPENAI_AGENTS.value,
            artifact_ref="source://basic@fingerprint-test",
            image_ref="ghcr.io/example/basic:latest",
        )
    )
    projector = RunExecutionProjector()

    record = projector.project_runtime_success(
        context,
        PublishedRunExecutionResult(
            runtime_result=RuntimeExecutionResult(
                output="Projected success output",
                latency_ms=17,
                token_usage=31,
                provider="mock",
                execution_backend="local",
            ),
            trace_events=[
                TraceIngestEvent(
                    run_id=run_id,
                    span_id=f"span-{run_id}-1",
                    step_type=StepType.LLM,
                    name="gpt-5.4-mini",
                    input={"prompt": "Explain the plan."},
                    output={"output": "Projected success output", "success": True},
                    metadata=TraceTelemetryMetadata(agent_id="basic"),
                )
            ],
        ),
    )

    metadata = record.events[0].metadata
    assert metadata is not None
    assert metadata.framework == AdapterKind.OPENAI_AGENTS.value
    assert metadata.artifact_ref == "source://basic@fingerprint-test"
    assert metadata.image_ref == "ghcr.io/example/basic:latest"
    assert metadata.runner_backend == "local-process"


def test_execution_recorder_ingests_trace_into_step_span_and_metrics():
    run_id = uuid4()
    run_repository = StateRunRepository()
    trajectory_repository = StateTrajectoryRepository()
    trace_repository = StateTraceRepository()

    run_repository.save(
        RunRecord(
            run_id=run_id,
            input_summary="record metrics",
            project="control-plane",
            dataset="crm-v2",
            model="gpt-5.4-mini",
            agent_type=AdapterKind.OPENAI_AGENTS,
            status=RunStatus.RUNNING,
        )
    )

    context = RunExecutionContext.from_spec(
        run_id,
        ExecutionRunSpec(
            project="control-plane",
            dataset="crm-v2",
            model="gpt-5.4-mini",
            agent_type=AdapterKind.OPENAI_AGENTS,
            input_summary="record metrics",
            prompt="Record this execution.",
        ),
    )
    projector = RunExecutionProjector()
    recorder = ExecutionRecorder(
        sink=RunExecutionStateSink(
            run_repository=run_repository,
            observation_sink=_build_telemetry_ingestor(
                run_repository=run_repository,
                trace_repository=trace_repository,
                trajectory_repository=trajectory_repository,
            ),
        ),
    )

    recorder.record(
        run_id,
        projector.project_runtime_success(
            context,
            PublishedRunExecutionResult(
                runtime_result=RuntimeExecutionResult(
                    output="ok",
                    latency_ms=9,
                    token_usage=13,
                    provider="mock",
                )
            ),
        ),
    )

    run = run_repository.get(run_id)
    steps = trajectory_repository.list_for_run(run_id)
    spans = trace_repository.list_for_run(run_id)

    assert run is not None
    assert run.latency_ms == 9
    assert run.token_cost == 13
    assert run.tool_calls == 0
    assert run.tracing is not None
    assert run.tracing.backend == "phoenix"
    expected_span_ids = [f"span-{run_id}-1"]
    assert [step.id for step in steps] == expected_span_ids
    assert [step.parent_step_id for step in steps] == [None]
    assert [span.span_id for span in spans] == expected_span_ids


def test_execution_recorder_ingests_runtime_trace_events_and_tool_metrics():
    run_id = uuid4()
    run_repository = StateRunRepository()
    trajectory_repository = StateTrajectoryRepository()
    trace_repository = StateTraceRepository()

    run_repository.save(
        RunRecord(
            run_id=run_id,
            input_summary="record tool metrics",
            project="control-plane",
            dataset="crm-v2",
            model="gpt-5.4-mini",
            agent_type=AdapterKind.OPENAI_AGENTS,
            status=RunStatus.RUNNING,
        )
    )

    context = RunExecutionContext.from_spec(
        run_id,
        ExecutionRunSpec(
            project="control-plane",
            dataset="crm-v2",
            model="gpt-5.4-mini",
            agent_type=AdapterKind.OPENAI_AGENTS,
            input_summary="record tool metrics",
            prompt="Use the tool before answering.",
        ),
    )
    projector = RunExecutionProjector()
    recorder = ExecutionRecorder(
        sink=RunExecutionStateSink(
            run_repository=run_repository,
            observation_sink=_build_telemetry_ingestor(
                run_repository=run_repository,
                trace_repository=trace_repository,
                trajectory_repository=trajectory_repository,
            ),
        ),
    )

    recorder.record(
        run_id,
        projector.project_runtime_success(
            context,
            PublishedRunExecutionResult(
                runtime_result=RuntimeExecutionResult(
                    output="done",
                    latency_ms=12,
                    token_usage=21,
                    provider="openai-agents-sdk",
                ),
                trace_events=[
                    TraceIngestEvent(
                        run_id=run_id,
                        span_id=f"span-{run_id}-1",
                        step_type=StepType.LLM,
                        name="gpt-5.4-mini",
                        input={"prompt": "Use the tool before answering.", "model": "gpt-5.4-mini"},
                        output={
                            "output": (
                                'tool_call: lookup_shipping_window({"order_reference":"A-1024"})'
                            )
                        },
                        token_usage=8,
                    ),
                    TraceIngestEvent(
                        run_id=run_id,
                        span_id=f"span-{run_id}-2",
                        parent_span_id=f"span-{run_id}-1",
                        step_type=StepType.TOOL,
                        name="lookup_shipping_window",
                        input={"prompt": '{"order_reference":"A-1024"}'},
                        output={"output": "eta_window=2 business days"},
                        tool_name="lookup_shipping_window",
                    ),
                    TraceIngestEvent(
                        run_id=run_id,
                        span_id=f"span-{run_id}-3",
                        parent_span_id=f"span-{run_id}-2",
                        step_type=StepType.LLM,
                        name="gpt-5.4-mini",
                        input={
                            "prompt": (
                                "Tool outputs:\n"
                                "lookup_shipping_window: eta_window=2 business days"
                            )
                        },
                        output={"output": "ETA is 2 business days."},
                        token_usage=13,
                    ),
                ],
            ),
        ),
    )

    run = run_repository.get(run_id)
    steps = trajectory_repository.list_for_run(run_id)

    assert run is not None
    assert run.latency_ms == 12
    assert run.token_cost == 21
    assert run.tool_calls == 1
    assert [step.step_type for step in steps] == [StepType.LLM, StepType.TOOL, StepType.LLM]
    assert [step.parent_step_id for step in steps] == [
        None,
        f"span-{run_id}-1",
        f"span-{run_id}-2",
    ]


def test_run_execution_service_records_structured_failure_details():
    run_id = uuid4()
    run_repository = StateRunRepository()
    trajectory_repository = StateTrajectoryRepository()
    trace_repository = StateTraceRepository()

    run_repository.save(
        RunRecord(
            run_id=run_id,
            input_summary="record failure",
            project="control-plane",
            dataset="crm-v2",
            agent_id="basic",
            model="gpt-5.4-mini",
            entrypoint="tests.fixtures.agents.basic:build_agent",
            agent_type=AdapterKind.OPENAI_AGENTS,
            status=RunStatus.QUEUED,
        )
    )

    class ExplodingPublishedRuntime:
        def execute(self, *_args, **_kwargs):
            raise ProviderAuthError("provider authentication failed")

    from app.execution.application import RunExecutionService

    service = RunExecutionService(
        artifact_resolver=_FixedArtifactResolver(),
        runner=ExplodingPublishedRuntime(),
        sink=RunExecutionStateSink(
            run_repository=run_repository,
            observation_sink=_build_telemetry_ingestor(
                run_repository=run_repository,
                trace_repository=trace_repository,
                trajectory_repository=trajectory_repository,
            ),
        ),
    )

    payload = ExecutionRunSpec(
        project="control-plane",
        dataset="crm-v2",
        agent_id="basic",
        model="gpt-5.4-mini",
        entrypoint="tests.fixtures.agents.basic:build_agent",
        agent_type=AdapterKind.OPENAI_AGENTS,
        input_summary="record failure",
        prompt="Trigger a failure.",
        executor_config=ExecutorConfig(backend="local-runner"),
    )

    service.execute_run(run_id, payload)

    run = run_repository.get(run_id)
    steps = trajectory_repository.list_for_run(run_id)

    assert run is not None
    assert run.status == RunStatus.FAILED
    assert run.entrypoint == "tests.fixtures.agents.basic:build_agent"
    assert run.runner_backend == "local-process"
    assert run.artifact_ref == "source://basic@fingerprint-test"
    assert run.error_code == "provider_call"
    assert run.error_message == "provider authentication failed"
    assert run.termination_reason == "provider authentication failed"
    assert len(steps) == 1
    assert steps[0].output == "live execution failed: provider authentication failed"


def test_run_execution_service_normalizes_framework_mismatch_as_agent_load():
    run_id = uuid4()
    run_repository = StateRunRepository()
    trajectory_repository = StateTrajectoryRepository()
    trace_repository = StateTraceRepository()

    run_repository.save(
        RunRecord(
            run_id=run_id,
            input_summary="framework mismatch",
            project="control-plane",
            dataset="crm-v2",
            agent_id="basic",
            model="gpt-5.4-mini",
            entrypoint="tests.fixtures.agents.basic:build_agent",
            agent_type=AdapterKind.OPENAI_AGENTS,
            status=RunStatus.QUEUED,
        )
    )

    class ExplodingPublishedRuntime:
        def execute(self, *_args, **_kwargs):
            raise AgentFrameworkMismatchError(
                "framework mismatch",
                agent_id="basic",
                expected_framework="openai-agents-sdk",
                actual_framework="langgraph",
            )

    from app.execution.application import RunExecutionService

    service = RunExecutionService(
        artifact_resolver=_FixedArtifactResolver(),
        runner=ExplodingPublishedRuntime(),
        sink=RunExecutionStateSink(
            run_repository=run_repository,
            observation_sink=_build_telemetry_ingestor(
                run_repository=run_repository,
                trace_repository=trace_repository,
                trajectory_repository=trajectory_repository,
            ),
        ),
    )

    payload = ExecutionRunSpec(
        project="control-plane",
        dataset="crm-v2",
        agent_id="basic",
        model="gpt-5.4-mini",
        entrypoint="tests.fixtures.agents.basic:build_agent",
        agent_type=AdapterKind.OPENAI_AGENTS,
        input_summary="framework mismatch",
        prompt="Trigger a framework mismatch.",
        executor_config=ExecutorConfig(backend="local-runner"),
    )

    service.execute_run(run_id, payload)

    run = run_repository.get(run_id)

    assert run is not None
    assert run.status == RunStatus.FAILED
    assert run.error_code == "agent_load"
    assert run.error_message == "framework mismatch"


def test_run_execution_service_normalizes_payload_run_id_to_target_run_id():
    run_id = uuid4()
    run_repository = StateRunRepository()
    trajectory_repository = StateTrajectoryRepository()
    trace_repository = StateTraceRepository()

    run_repository.save(
        RunRecord(
            run_id=run_id,
            input_summary="normalize run id",
            project="control-plane",
            dataset="crm-v2",
            agent_id="basic",
            model="gpt-5.4-mini",
            entrypoint="tests.fixtures.agents.basic:build_agent",
            agent_type=AdapterKind.OPENAI_AGENTS,
            status=RunStatus.QUEUED,
        )
    )

    captured: dict[str, object] = {}

    class CapturingRunner:
        def execute(self, payload):
            captured["payload"] = payload
            return RunnerExecutionResult(
                runner_backend="local-process",
                artifact_ref="source://basic@fingerprint-test",
                image_ref=None,
                execution=PublishedRunExecutionResult(
                    runtime_result=RuntimeExecutionResult(
                        output="ok",
                        latency_ms=5,
                        token_usage=8,
                        provider="mock",
                        resolved_model="gpt-5.4-mini",
                    ),
                    trace_events=[
                        TraceIngestEvent(
                            run_id=payload.run_id,
                            span_id=f"span-{payload.run_id}-1",
                            step_type=StepType.LLM,
                            name=payload.model,
                            input={"prompt": payload.prompt},
                            output={"output": "ok", "success": True},
                        )
                    ],
                ),
            )

    from app.execution.application import RunExecutionService

    service = RunExecutionService(
        artifact_resolver=_FixedArtifactResolver(),
        runner=CapturingRunner(),
        sink=RunExecutionStateSink(
            run_repository=run_repository,
            observation_sink=_build_telemetry_ingestor(
                run_repository=run_repository,
                trace_repository=trace_repository,
                trajectory_repository=trajectory_repository,
            ),
        ),
    )

    payload = ExecutionRunSpec(
        project="control-plane",
        dataset="crm-v2",
        agent_id="basic",
        model="gpt-5.4-mini",
        entrypoint="tests.fixtures.agents.basic:build_agent",
        agent_type=AdapterKind.OPENAI_AGENTS,
        input_summary="normalize run id",
        prompt="Keep correlation stable.",
        executor_config=ExecutorConfig(backend="local-runner"),
    )

    assert payload.run_id != run_id

    service.execute_run(run_id, payload)

    runner_payload = captured["payload"]
    run = run_repository.get(run_id)
    steps = trajectory_repository.list_for_run(run_id)

    assert runner_payload.run_id == run_id
    assert run is not None
    assert run.status == RunStatus.SUCCEEDED
    assert [step.run_id for step in steps] == [run_id]


def test_run_execution_service_enriches_projector_context_with_runner_submission_metadata():
    run_id = uuid4()
    run_repository = StateRunRepository()
    trajectory_repository = StateTrajectoryRepository()
    trace_repository = StateTraceRepository()

    run_repository.save(
        RunRecord(
            run_id=run_id,
            input_summary="projector metadata context",
            project="control-plane",
            dataset="crm-v2",
            agent_id="basic",
            model="gpt-5.4-mini",
            entrypoint="tests.fixtures.agents.basic:build_agent",
            agent_type=AdapterKind.OPENAI_AGENTS,
            status=RunStatus.QUEUED,
        )
    )

    captured: dict[str, object] = {}

    class StubRunner:
        def execute(self, payload):
            return RunnerExecutionResult(
                runner_backend=payload.runner_backend or "local-process",
                artifact_ref=payload.artifact_ref,
                image_ref=payload.image_ref,
                execution=PublishedRunExecutionResult(
                    runtime_result=RuntimeExecutionResult(
                        output="ok",
                        latency_ms=5,
                        token_usage=8,
                        provider="mock",
                        resolved_model="gpt-5.4-mini",
                    )
                ),
            )

    class CapturingProjector:
        def project_runtime_success(self, context, result):
            captured["context"] = context
            return ProjectedExecutionRecord(events=[], metrics=ExecutionMetrics())

        def project_runtime_failure(self, context, error):
            captured["failure_context"] = context
            return ProjectedExecutionRecord(events=[], metrics=ExecutionMetrics())

    from app.execution.application import RunExecutionService

    service = RunExecutionService(
        artifact_resolver=_FixedArtifactResolver(),
        runner=StubRunner(),
        sink=RunExecutionStateSink(
            run_repository=run_repository,
            observation_sink=_build_telemetry_ingestor(
                run_repository=run_repository,
                trace_repository=trace_repository,
                trajectory_repository=trajectory_repository,
            ),
        ),
        projector=CapturingProjector(),
    )

    payload = ExecutionRunSpec(
        project="control-plane",
        dataset="crm-v2",
        agent_id="basic",
        model="gpt-5.4-mini",
        entrypoint="tests.fixtures.agents.basic:build_agent",
        agent_type=AdapterKind.OPENAI_AGENTS,
        input_summary="projector metadata context",
        prompt="Keep metadata stable.",
        executor_config=ExecutorConfig(backend="local-runner"),
    )

    service.execute_run(run_id, payload)

    context = captured["context"]
    assert context.runner_submission is not None
    assert context.runner_submission.runner_backend == "local-process"
    assert context.runner_submission.framework == AdapterKind.OPENAI_AGENTS.value
    assert context.runner_submission.artifact_ref == "source://basic@fingerprint-test"


def test_run_execution_service_uses_k8s_runner_backend_for_k8s_executor():
    run_id = uuid4()
    run_repository = StateRunRepository()
    trajectory_repository = StateTrajectoryRepository()
    trace_repository = StateTraceRepository()

    run_repository.save(
        RunRecord(
            run_id=run_id,
            input_summary="k8s backend selection",
            project="control-plane",
            dataset="crm-v2",
            agent_id="basic",
            model="gpt-5.4-mini",
            entrypoint="tests.fixtures.agents.basic:build_agent",
            agent_type=AdapterKind.OPENAI_AGENTS,
            status=RunStatus.QUEUED,
        )
    )

    captured: dict[str, object] = {}

    class CapturingRunner:
        def execute(self, payload):
            captured["payload"] = payload
            return RunnerExecutionResult(
                runner_backend=payload.runner_backend,
                artifact_ref=payload.artifact_ref,
                image_ref=payload.image_ref,
                execution=PublishedRunExecutionResult(
                    runtime_result=RuntimeExecutionResult(
                        output="ok",
                        latency_ms=5,
                        token_usage=8,
                        provider="mock",
                        resolved_model="gpt-5.4-mini",
                    )
                ),
            )

    from app.execution.application import RunExecutionService

    service = RunExecutionService(
        artifact_resolver=_FixedArtifactResolver(),
        runner=CapturingRunner(),
        sink=RunExecutionStateSink(
            run_repository=run_repository,
            observation_sink=_build_telemetry_ingestor(
                run_repository=run_repository,
                trace_repository=trace_repository,
                trajectory_repository=trajectory_repository,
            ),
        ),
        default_runner_backend="local-process",
    )

    payload = ExecutionRunSpec(
        project="control-plane",
        dataset="crm-v2",
        agent_id="basic",
        model="gpt-5.4-mini",
        entrypoint="tests.fixtures.agents.basic:build_agent",
        agent_type=AdapterKind.OPENAI_AGENTS,
        input_summary="k8s backend selection",
        prompt="Launch on k8s.",
        executor_config=ExecutorConfig(backend="k8s-job"),
    )

    service.execute_run(run_id, payload)

    runner_payload = captured["payload"]
    assert runner_payload.runner_backend == "k8s-container"


def test_run_execution_service_uses_configured_runner_backend_for_external_runner():
    run_id = uuid4()
    run_repository = StateRunRepository()
    trajectory_repository = StateTrajectoryRepository()
    trace_repository = StateTraceRepository()

    run_repository.save(
        RunRecord(
            run_id=run_id,
            input_summary="external runner carrier selection",
            project="control-plane",
            dataset="crm-v2",
            agent_id="basic",
            model="gpt-5.4-mini",
            entrypoint="tests.fixtures.agents.basic:build_agent",
            agent_type=AdapterKind.OPENAI_AGENTS,
            status=RunStatus.QUEUED,
        )
    )

    captured: dict[str, object] = {}

    class CapturingRunner:
        def execute(self, payload):
            captured["payload"] = payload
            return RunnerExecutionResult(
                runner_backend=payload.runner_backend,
                artifact_ref=payload.artifact_ref,
                image_ref=payload.image_ref,
                execution=PublishedRunExecutionResult(
                    runtime_result=RuntimeExecutionResult(
                        output="ok",
                        latency_ms=5,
                        token_usage=8,
                        provider="mock",
                        resolved_model="gpt-5.4-mini",
                    )
                ),
            )

    from app.execution.application import RunExecutionService

    service = RunExecutionService(
        artifact_resolver=_FixedArtifactResolver(),
        runner=CapturingRunner(),
        sink=RunExecutionStateSink(
            run_repository=run_repository,
            observation_sink=_build_telemetry_ingestor(
                run_repository=run_repository,
                trace_repository=trace_repository,
                trajectory_repository=trajectory_repository,
            ),
        ),
        default_runner_backend="local-process",
    )

    payload = ExecutionRunSpec(
        project="control-plane",
        dataset="crm-v2",
        agent_id="basic",
        model="gpt-5.4-mini",
        entrypoint="tests.fixtures.agents.basic:build_agent",
        agent_type=AdapterKind.OPENAI_AGENTS,
        input_summary="external runner carrier selection",
        prompt="Launch Claude Code via K8s carrier.",
        executor_config=ExecutorConfig(
            backend="external-runner",
            execution_binding=ExecutionBinding(
                runner_backend="k8s-container",
                runner_image="ghcr.io/example/claude-runner:latest",
                config={
                    "claude_code_cli": {
                        "command": "claude",
                        "args": ["--dangerously-skip-permissions"],
                    },
                },
            ),
        ),
    )

    service.execute_run(run_id, payload)

    runner_payload = captured["payload"]
    assert runner_payload.runner_backend == "k8s-container"


def test_run_execution_service_respects_non_k8s_runner_backend_override_for_external_runner():
    run_id = uuid4()
    run_repository = StateRunRepository()
    trajectory_repository = StateTrajectoryRepository()
    trace_repository = StateTraceRepository()

    run_repository.save(
        RunRecord(
            run_id=run_id,
            input_summary="external runner docker carrier selection",
            project="control-plane",
            dataset="crm-v2",
            agent_id="basic",
            model="gpt-5.4-mini",
            entrypoint="tests.fixtures.agents.basic:build_agent",
            agent_type=AdapterKind.OPENAI_AGENTS,
            status=RunStatus.QUEUED,
        )
    )

    captured: dict[str, object] = {}

    class CapturingRunner:
        def execute(self, payload):
            captured["payload"] = payload
            return RunnerExecutionResult(
                runner_backend=payload.runner_backend,
                artifact_ref=payload.artifact_ref,
                image_ref=payload.image_ref,
                execution=PublishedRunExecutionResult(
                    runtime_result=RuntimeExecutionResult(
                        output="ok",
                        latency_ms=5,
                        token_usage=8,
                        provider="mock",
                        resolved_model="gpt-5.4-mini",
                    )
                ),
            )

    from app.execution.application import RunExecutionService

    service = RunExecutionService(
        artifact_resolver=_FixedArtifactResolver(),
        runner=CapturingRunner(),
        sink=RunExecutionStateSink(
            run_repository=run_repository,
            observation_sink=_build_telemetry_ingestor(
                run_repository=run_repository,
                trace_repository=trace_repository,
                trajectory_repository=trajectory_repository,
            ),
        ),
        default_runner_backend="local-process",
    )

    payload = ExecutionRunSpec(
        project="control-plane",
        dataset="crm-v2",
        agent_id="basic",
        model="gpt-5.4-mini",
        entrypoint="tests.fixtures.agents.basic:build_agent",
        agent_type=AdapterKind.OPENAI_AGENTS,
        input_summary="external runner docker carrier selection",
        prompt="Launch Claude Code via local docker carrier.",
        executor_config=ExecutorConfig(
            backend="external-runner",
            execution_binding=ExecutionBinding(
                runner_backend="docker-container",
                runner_image="atlas-claude-validation:local",
                config={
                    "claude_code_cli": {
                        "command": "claude",
                        "args": ["--dangerously-skip-permissions"],
                    },
                },
            ),
        ),
    )

    service.execute_run(run_id, payload)

    runner_payload = captured["payload"]
    assert runner_payload.runner_backend == "docker-container"


def test_run_execution_service_keeps_local_runner_explicitly_local():
    run_id = uuid4()
    run_repository = StateRunRepository()
    trajectory_repository = StateTrajectoryRepository()
    trace_repository = StateTraceRepository()

    run_repository.save(
        RunRecord(
            run_id=run_id,
            input_summary="local backend selection",
            project="control-plane",
            dataset="crm-v2",
            agent_id="basic",
            model="gpt-5.4-mini",
            entrypoint="tests.fixtures.agents.basic:build_agent",
            agent_type=AdapterKind.OPENAI_AGENTS,
            status=RunStatus.QUEUED,
        )
    )

    captured: dict[str, object] = {}

    class CapturingRunner:
        def execute(self, payload):
            captured["payload"] = payload
            return RunnerExecutionResult(
                runner_backend=payload.runner_backend,
                artifact_ref=payload.artifact_ref,
                image_ref=payload.image_ref,
                execution=PublishedRunExecutionResult(
                    runtime_result=RuntimeExecutionResult(
                        output="ok",
                        latency_ms=5,
                        token_usage=8,
                        provider="mock",
                        resolved_model="gpt-5.4-mini",
                    )
                ),
            )

    from app.execution.application import RunExecutionService

    service = RunExecutionService(
        artifact_resolver=_FixedArtifactResolver(),
        runner=CapturingRunner(),
        sink=RunExecutionStateSink(
            run_repository=run_repository,
            observation_sink=_build_telemetry_ingestor(
                run_repository=run_repository,
                trace_repository=trace_repository,
                trajectory_repository=trajectory_repository,
            ),
        ),
        default_runner_backend="k8s-container",
    )

    payload = ExecutionRunSpec(
        project="control-plane",
        dataset="crm-v2",
        agent_id="basic",
        model="gpt-5.4-mini",
        entrypoint="tests.fixtures.agents.basic:build_agent",
        agent_type=AdapterKind.OPENAI_AGENTS,
        input_summary="local backend selection",
        prompt="Stay local.",
        executor_config=ExecutorConfig(backend="local-runner"),
    )

    service.execute_run(run_id, payload)

    runner_payload = captured["payload"]
    assert runner_payload.runner_backend == "local-process"


def test_run_execution_service_marks_execution_cancelled_without_failure_record():
    run_id = uuid4()
    run_repository = StateRunRepository()
    trajectory_repository = StateTrajectoryRepository()
    trace_repository = StateTraceRepository()

    run_repository.save(
        RunRecord(
            run_id=run_id,
            input_summary="cancelled during execution",
            project="control-plane",
            dataset="crm-v2",
            agent_id="basic",
            model="gpt-5.4-mini",
            entrypoint="tests.fixtures.agents.basic:build_agent",
            agent_type=AdapterKind.OPENAI_AGENTS,
            status=RunStatus.QUEUED,
        )
    )

    class CancellingRunner:
        def execute(self, payload):
            run = run_repository.get(payload.run_id)
            assert run is not None
            run_repository.save(run.model_copy(update={"status": RunStatus.CANCELLING}))
            raise ExecutionCancelled()

    from app.execution.application import RunExecutionService

    service = RunExecutionService(
        artifact_resolver=_FixedArtifactResolver(),
        runner=CancellingRunner(),
        sink=RunExecutionStateSink(
            run_repository=run_repository,
            observation_sink=_build_telemetry_ingestor(
                run_repository=run_repository,
                trace_repository=trace_repository,
                trajectory_repository=trajectory_repository,
            ),
        ),
    )

    payload = ExecutionRunSpec(
        project="control-plane",
        dataset="crm-v2",
        agent_id="basic",
        model="gpt-5.4-mini",
        entrypoint="tests.fixtures.agents.basic:build_agent",
        agent_type=AdapterKind.OPENAI_AGENTS,
        input_summary="cancelled during execution",
        prompt="Cancel this run.",
        executor_config=ExecutorConfig(backend="local-runner"),
    )

    service.execute_run(run_id, payload)

    run = run_repository.get(run_id)
    steps = trajectory_repository.list_for_run(run_id)

    assert run is not None
    assert run.status == RunStatus.CANCELLED
    assert run.error_code is None
    assert run.error_message is None
    assert steps == []


def test_run_execution_service_marks_failed_runs_from_failed_trace_events():
    run_id = uuid4()
    run_repository = StateRunRepository()
    trajectory_repository = StateTrajectoryRepository()
    trace_repository = StateTraceRepository()

    run_repository.save(
        RunRecord(
            run_id=run_id,
            input_summary="record tool failure trace",
            project="control-plane",
            dataset="fulfillment-eval-v1",
            agent_id="fulfillment_ops",
            model="gpt-5.4-mini",
            entrypoint="tests.fixtures.agents.fulfillment_ops:build_agent",
            agent_type=AdapterKind.OPENAI_AGENTS,
            status=RunStatus.QUEUED,
        )
    )

    class FailedToolPublishedRuntime:
        def execute(self, *_args, **_kwargs):
            return RunnerExecutionResult(
                runner_backend="local-process",
                artifact_ref="source://fulfillment_ops@fingerprint-test",
                image_ref=None,
                execution=PublishedRunExecutionResult(
                    runtime_result=RuntimeExecutionResult(
                        output="success",
                        latency_ms=15,
                        token_usage=18,
                        provider="openai-agents-sdk",
                        resolved_model="gpt-5.4-mini",
                    ),
                    trace_events=[
                        TraceIngestEvent(
                            run_id=run_id,
                            span_id=f"span-{run_id}-1",
                            step_type=StepType.LLM,
                            name="gpt-5.4-mini",
                            input={
                                "prompt": (
                                    "Order ORD-ERR-100 is delayed. "
                                    "Check status and decide the next action."
                                ),
                                "model": "gpt-5.4-mini",
                            },
                            output={
                                "output": (
                                    "tool_call: " 'lookup_order_status({"order_id":"ORD-ERR-100"})'
                                ),
                                "success": True,
                            },
                            token_usage=8,
                        ),
                        TraceIngestEvent(
                            run_id=run_id,
                            span_id=f"span-{run_id}-2",
                            parent_span_id=f"span-{run_id}-1",
                            step_type=StepType.TOOL,
                            name="lookup_order_status",
                            input={"prompt": '{"order_id":"ORD-ERR-100"}'},
                            output={
                                "output": (
                                    "An error occurred while running the tool. Please try again. "
                                    "Error: tool backend unavailable for order 'ORD-ERR-100'"
                                ),
                                "success": False,
                                "error": "tool backend unavailable for order 'ORD-ERR-100'",
                            },
                            tool_name="lookup_order_status",
                        ),
                        TraceIngestEvent(
                            run_id=run_id,
                            span_id=f"span-{run_id}-3",
                            parent_span_id=f"span-{run_id}-2",
                            step_type=StepType.LLM,
                            name="gpt-5.4-mini",
                            input={
                                "prompt": (
                                    "Order ORD-ERR-100 is delayed. Check status and decide the "
                                    "next action.\n\nTool outputs:\nlookup_order_status: An "
                                    "error occurred while running the tool. Please try again. "
                                    "Error: tool backend unavailable for order 'ORD-ERR-100'"
                                )
                            },
                            output={
                                "output": "success",
                                "success": False,
                                "error": "tool backend unavailable for order 'ORD-ERR-100'",
                            },
                            token_usage=10,
                        ),
                    ],
                ),
            )

    from app.execution.application import RunExecutionService

    service = RunExecutionService(
        artifact_resolver=_FixedArtifactResolver(),
        runner=FailedToolPublishedRuntime(),
        sink=RunExecutionStateSink(
            run_repository=run_repository,
            observation_sink=_build_telemetry_ingestor(
                run_repository=run_repository,
                trace_repository=trace_repository,
                trajectory_repository=trajectory_repository,
            ),
        ),
    )

    payload = ExecutionRunSpec(
        project="control-plane",
        dataset="fulfillment-eval-v1",
        agent_id="fulfillment_ops",
        model="gpt-5.4-mini",
        entrypoint="tests.fixtures.agents.fulfillment_ops:build_agent",
        agent_type=AdapterKind.OPENAI_AGENTS,
        input_summary="record tool failure trace",
        prompt="Order ORD-ERR-100 is delayed. Check status and decide the next action.",
        executor_config=ExecutorConfig(backend="local-runner"),
    )

    service.execute_run(run_id, payload)

    run = run_repository.get(run_id)
    steps = trajectory_repository.list_for_run(run_id)

    assert run is not None
    assert run.status == RunStatus.FAILED
    assert run.runner_backend == "local-process"
    assert run.artifact_ref == "source://fulfillment_ops@fingerprint-test"
    assert run.error_code == "tool_execution"
    assert run.error_message == "tool backend unavailable for order 'ORD-ERR-100'"
    assert run.termination_reason == "tool backend unavailable for order 'ORD-ERR-100'"
    assert run.latency_ms == 15
    assert run.token_cost == 18
    assert run.tool_calls == 1
    assert [step.success for step in steps] == [True, False, False]


def test_run_execution_projector_handles_prompt_only_run():
    run_id = uuid4()
    context = RunExecutionContext.from_spec(
        run_id,
        ExecutionRunSpec(
            project="control-plane",
            dataset=None,
            model="gpt-5.4-mini",
            agent_type=AdapterKind.OPENAI_AGENTS,
            input_summary="prompt only",
            prompt="Explain the plan.",
        ),
    )
    projector = RunExecutionProjector()

    record = projector.project_runtime_success(
        context,
        PublishedRunExecutionResult(
            runtime_result=RuntimeExecutionResult(
                output="ok",
                latency_ms=7,
                token_usage=11,
                provider="mock",
            )
        ),
    )

    assert record.events[0].input["prompt"] == "Explain the plan."
    assert record.events[0].input["model"] == "gpt-5.4-mini"
