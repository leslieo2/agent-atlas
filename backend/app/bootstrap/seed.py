from __future__ import annotations

from contextlib import suppress
from uuid import UUID

from app.bootstrap.container import AppContainer, get_container
from app.core.errors import AgentValidationFailedError
from app.modules.datasets.domain.models import Dataset, DatasetSample
from app.modules.runs.domain.models import RunRecord, TrajectoryStep
from app.modules.shared.domain.enums import AdapterKind, RunStatus, StepType


def seed_demo_state(container: AppContainer | None = None) -> None:
    container = container or get_container()
    if container.dataset_queries.list():
        return

    for agent_id in ("basic", "customer_service", "tools"):
        with suppress(AgentValidationFailedError):
            container.agent_publication_commands.publish(agent_id)

    def _agent_snapshot(agent_id: str) -> dict[str, object]:
        published = container.published_agent_repository.get_agent(agent_id)
        if published is None:
            return {}
        return {"agent_snapshot": published.to_snapshot()}

    seeded_runs = [
        RunRecord(
            run_id=UUID("a6f3f2a1-1111-4f8d-9999-111111111111"),
            input_summary="Generate a booking itinerary from CRM contact data",
            status=RunStatus.SUCCEEDED,
            latency_ms=1410,
            token_cost=1280,
            tool_calls=5,
            project="sales-assistant",
            dataset="crm-v2",
            agent_id="customer_service",
            model="gpt-4.1-mini",
            agent_type=AdapterKind.OPENAI_AGENTS,
            tags=["example", "support"],
            project_metadata=_agent_snapshot("customer_service"),
        ),
        RunRecord(
            run_id=UUID("a6f3f2a1-2222-4f8d-9999-111111111111"),
            input_summary="Summarize latest support tickets and escalate exceptions",
            status=RunStatus.FAILED,
            latency_ms=960,
            token_cost=910,
            tool_calls=3,
            project="support-router",
            dataset="support-incidents",
            agent_id="customer_service",
            model="gpt-5-mini",
            agent_type=AdapterKind.OPENAI_AGENTS,
            tags=["example", "support"],
            project_metadata=_agent_snapshot("customer_service"),
        ),
        RunRecord(
            run_id=UUID("a6f3f2a1-3333-4f8d-9999-111111111111"),
            input_summary="Analyze policy document and extract exceptions",
            status=RunStatus.RUNNING,
            latency_ms=0,
            token_cost=460,
            tool_calls=2,
            project="policy-lab",
            dataset="policy-review",
            agent_id="basic",
            model="gpt-4.1",
            agent_type=AdapterKind.OPENAI_AGENTS,
            tags=["example", "smoke"],
            project_metadata=_agent_snapshot("basic"),
        ),
        RunRecord(
            run_id=UUID("a6f3f2a1-4444-4f8d-9999-111111111111"),
            input_summary="Run benchmark against shopping agent benchmark",
            status=RunStatus.QUEUED,
            latency_ms=0,
            token_cost=0,
            tool_calls=0,
            project="benchmarking",
            dataset="shopping-bench",
            agent_id="tools",
            model="gpt-4.1-mini",
            agent_type=AdapterKind.OPENAI_AGENTS,
            tags=["example", "tools"],
            project_metadata=_agent_snapshot("tools"),
        ),
    ]
    seeded_steps = {
        UUID("a6f3f2a1-1111-4f8d-9999-111111111111"): [
            TrajectoryStep(
                id="seed-step-001",
                run_id=UUID("a6f3f2a1-1111-4f8d-9999-111111111111"),
                step_type=StepType.PLANNER,
                parent_step_id=None,
                prompt="Plan retrieval sequence for user request and required tools.",
                output="Detected required tools: crm_lookup, itinerary_builder, pricing_service",
                model=None,
                temperature=0.1,
                latency_ms=250,
                token_usage=220,
                success=True,
            ),
            TrajectoryStep(
                id="seed-step-002",
                run_id=UUID("a6f3f2a1-1111-4f8d-9999-111111111111"),
                step_type=StepType.TOOL,
                parent_step_id="seed-step-001",
                prompt='input: {"contact_id":"ac-119","scope":"shipping"}',
                output=(
                    '{"profile":"tier: gold","history":["ticket-901","ticket-905"],'
                    '"preferred_carrier":"FedEx"}'
                ),
                model="n/a",
                temperature=0,
                latency_ms=430,
                token_usage=0,
                success=True,
                tool_name="crm_lookup",
            ),
            TrajectoryStep(
                id="seed-step-003",
                run_id=UUID("a6f3f2a1-1111-4f8d-9999-111111111111"),
                step_type=StepType.LLM,
                parent_step_id="seed-step-002",
                prompt="Generate a safe itinerary draft from user context and tool responses.",
                output="Itinerary prepared with best-price shipping lane and ETA.",
                model="gpt-4.1",
                temperature=0.3,
                latency_ms=520,
                token_usage=310,
                success=True,
            ),
            TrajectoryStep(
                id="seed-step-004",
                run_id=UUID("a6f3f2a1-1111-4f8d-9999-111111111111"),
                step_type=StepType.TOOL,
                parent_step_id="seed-step-001",
                prompt='input: {"from":"PVG","to":"SFO","weight_kg":2.1}',
                output="quote_error: fallback route disabled for destination",
                model="n/a",
                temperature=0,
                latency_ms=140,
                token_usage=0,
                success=False,
                tool_name="pricing_service",
            ),
        ],
    }

    datasets = [
        Dataset(
            name="crm-v2",
            rows=[
                DatasetSample(sample_id="sample-001", input="Can you create a shipping itinerary?"),
                DatasetSample(
                    sample_id="sample-002",
                    input="What is fastest carrier from PVG to SFO?",
                ),
            ],
        ),
        Dataset(
            name="support-incidents",
            rows=[
                DatasetSample(sample_id="sample-101", input="Customer reported stale invoice"),
                DatasetSample(sample_id="sample-102", input="Account locked after 2 failed logins"),
            ],
        ),
    ]

    for run in seeded_runs:
        container.run_repository.save(run)
    for steps in seeded_steps.values():
        for step in steps:
            container.trajectory_repository.append(step)
    for dataset in datasets:
        container.dataset_repository.save(dataset)
