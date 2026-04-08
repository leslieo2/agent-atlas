from __future__ import annotations

import sqlite3
from pathlib import Path
from uuid import uuid4

from app.bootstrap.wiring.infrastructure import build_infrastructure
from app.core.config import settings
from app.db.persistence import PlaneStoreSet
from app.infrastructure import repositories as infrastructure_repositories
from app.infrastructure.repositories import reset_state
from app.modules.agents.adapters.outbound import StatePublishedAgentRepository
from app.modules.datasets.adapters.outbound import StateDatasetRepository
from app.modules.datasets.domain.models import Dataset, DatasetSample, DatasetVersion
from app.modules.experiments.adapters.outbound import (
    StateExperimentRepository,
    StateRunEvaluationRepository,
)
from app.modules.experiments.domain.models import (
    ExperimentRecord,
    ExperimentSpec,
    RunEvaluationRecord,
)
from app.modules.exports.adapters.outbound import StateExportRepository
from app.modules.exports.domain.models import ArtifactMetadata
from app.modules.policies.adapters.outbound import StateApprovalPolicyRepository
from app.modules.policies.domain.models import ApprovalPolicyRecord
from app.modules.runs.adapters.outbound import (
    StateRunRepository,
    StateTraceRepository,
    StateTrajectoryRepository,
)
from app.modules.runs.domain.models import RunRecord
from app.modules.shared.domain.enums import (
    AdapterKind,
    ArtifactFormat,
    PolicyEffect,
    RunStatus,
    SampleJudgement,
    StepType,
)
from app.modules.shared.domain.execution import ModelConfig
from app.modules.shared.domain.observability import TrajectoryStepRecord
from app.modules.shared.domain.policies import ToolPolicyRule
from app.modules.shared.domain.traces import TraceSpan
from tests.fixtures.agents.catalog import build_fixture_published_agent


def _sqlite_url(path: Path) -> str:
    return f"sqlite:///{path}"


def _sqlite_path(database_url: str | None) -> Path:
    assert database_url is not None
    prefix = "sqlite:///"
    assert database_url.startswith(prefix)
    return Path(database_url[len(prefix) :])


def _table_names(path: Path) -> set[str]:
    conn = sqlite3.connect(path)
    try:
        return {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
    finally:
        conn.close()


def _run_record() -> RunRecord:
    return RunRecord(
        run_id=uuid4(),
        input_summary="storage split",
        project="control-plane",
        dataset="crm-v2",
        model="gpt-5.4-mini",
        agent_type=AdapterKind.OPENAI_AGENTS,
        status=RunStatus.RUNNING,
    )


def _dataset() -> Dataset:
    version = DatasetVersion(
        dataset_name="crm-v2",
        version="v1",
        rows=[DatasetSample(sample_id="sample-1", input="hello", expected="world")],
    )
    return Dataset(
        name="crm-v2",
        current_version_id=version.dataset_version_id,
        versions=[version],
    )


def _experiment() -> ExperimentRecord:
    dataset = _dataset()
    return ExperimentRecord(
        name="exp-1",
        dataset_name=dataset.name,
        dataset_version_id=dataset.current_version_id,
        published_agent_id="basic",
        spec=ExperimentSpec(
            dataset_version_id=dataset.current_version_id,
            published_agent_id="basic",
            model_settings=ModelConfig(model="gpt-5.4-mini"),
        ),
    )


def _run_evaluation(experiment: ExperimentRecord, run: RunRecord) -> RunEvaluationRecord:
    return RunEvaluationRecord(
        experiment_id=experiment.experiment_id,
        dataset_version_id=experiment.dataset_version_id,
        dataset_sample_id="sample-1",
        run_id=run.run_id,
        judgement=SampleJudgement.PASSED,
        input="hello",
        actual="world",
    )


def _artifact() -> ArtifactMetadata:
    return ArtifactMetadata(
        format=ArtifactFormat.JSONL,
        path="s3://exports/atlas-run-1.jsonl",
        size_bytes=128,
        row_count=1,
    )


def _approval_policy() -> ApprovalPolicyRecord:
    return ApprovalPolicyRecord(
        name="default",
        tool_policies=[
            ToolPolicyRule(tool_name="lookup", effect=PolicyEffect.ALLOW),
        ],
    )


def test_runs_storage_owns_only_run_tables_and_round_trips(tmp_path: Path) -> None:
    db_path = tmp_path / "runs.db"
    stores = PlaneStoreSet(
        control_database_url=_sqlite_url(db_path),
        data_database_url=_sqlite_url(db_path),
    )
    try:
        run_repository = StateRunRepository(stores)
        trajectory_repository = StateTrajectoryRepository(stores)
        trace_repository = StateTraceRepository(stores)
        run = _run_record()

        run_repository.save(run)
        trajectory_repository.append(
            TrajectoryStepRecord(
                id="step-1",
                run_id=run.run_id,
                step_type=StepType.LLM,
                prompt="Explain the plan.",
                output="Plan explained.",
            )
        )
        trace_repository.append(
            TraceSpan(
                run_id=run.run_id,
                span_id="span-1",
                parent_span_id=None,
                step_type=StepType.LLM,
                input={"prompt": "Explain the plan."},
                output={"output": "Plan explained."},
                latency_ms=5,
                token_usage=11,
            )
        )

        assert run_repository.get(run.run_id) == run
        assert len(trajectory_repository.list_for_run(run.run_id)) == 1
        assert len(trace_repository.list_for_run(run.run_id)) == 1
        assert _table_names(db_path) == {
            "control_runs",
            "data_trace_spans",
            "data_trajectory",
        }
    finally:
        stores.close()


def test_datasets_storage_owns_only_dataset_tables_and_round_trips(tmp_path: Path) -> None:
    db_path = tmp_path / "datasets.db"
    stores = PlaneStoreSet(
        control_database_url=_sqlite_url(db_path),
        data_database_url=_sqlite_url(db_path),
    )
    try:
        repository = StateDatasetRepository(stores)
        dataset = _dataset()

        repository.save(dataset)

        assert repository.get(dataset.name) == dataset
        assert repository.get_version(dataset.current_version_id) == dataset.current_version()
        assert _table_names(db_path) == {"control_datasets", "control_dataset_versions"}
    finally:
        stores.close()


def test_experiments_storage_owns_only_experiment_tables_and_round_trips(tmp_path: Path) -> None:
    db_path = tmp_path / "experiments.db"
    stores = PlaneStoreSet(
        control_database_url=_sqlite_url(db_path),
        data_database_url=_sqlite_url(db_path),
    )
    try:
        experiment_repository = StateExperimentRepository(stores)
        evaluation_repository = StateRunEvaluationRepository(stores)
        experiment = _experiment()
        run = _run_record()
        evaluation = _run_evaluation(experiment, run)

        experiment_repository.save(experiment)
        evaluation_repository.save(evaluation)

        assert experiment_repository.get(experiment.experiment_id) == experiment
        assert evaluation_repository.get_by_run(run.run_id) == evaluation
        assert evaluation_repository.list_for_experiment(experiment.experiment_id) == [evaluation]
        assert _table_names(db_path) == {"control_experiments", "data_run_evaluations"}
    finally:
        stores.close()


def test_exports_storage_owns_only_artifact_table_and_round_trips(tmp_path: Path) -> None:
    db_path = tmp_path / "exports.db"
    stores = PlaneStoreSet(
        control_database_url=_sqlite_url(db_path),
        data_database_url=_sqlite_url(db_path),
    )
    try:
        repository = StateExportRepository(stores)
        artifact = _artifact()

        repository.save(artifact)

        assert repository.get(artifact.artifact_id) == artifact
        assert repository.list() == [artifact]
        assert _table_names(db_path) == {"data_artifacts"}
    finally:
        stores.close()


def test_policies_storage_owns_only_policy_tables_and_round_trips(tmp_path: Path) -> None:
    db_path = tmp_path / "policies.db"
    stores = PlaneStoreSet(
        control_database_url=_sqlite_url(db_path),
        data_database_url=_sqlite_url(db_path),
    )
    try:
        repository = StateApprovalPolicyRepository(stores)
        policy = _approval_policy()

        repository.save(policy)

        assert repository.get(policy.approval_policy_id) == policy
        assert repository.list() == [policy]
        assert _table_names(db_path) == {"control_approval_policies", "control_tool_policies"}
    finally:
        stores.close()


def test_agents_storage_owns_only_published_agent_table_and_round_trips(tmp_path: Path) -> None:
    db_path = tmp_path / "agents.db"
    stores = PlaneStoreSet(
        control_database_url=_sqlite_url(db_path),
        data_database_url=_sqlite_url(db_path),
    )
    try:
        repository = StatePublishedAgentRepository(stores)
        agent = build_fixture_published_agent("basic")

        repository.save_agent(agent)

        assert repository.get_agent(agent.agent_id) == agent
        assert repository.list_agents() == [agent]
        assert _table_names(db_path) == {"control_published_agents"}
    finally:
        stores.close()


def test_build_infrastructure_initializes_full_expected_table_set() -> None:
    build_infrastructure()

    assert _table_names(_sqlite_path(settings.control_plane_database_url)) >= {
        "control_runs",
        "control_datasets",
        "control_dataset_versions",
        "control_experiments",
        "control_approval_policies",
        "control_tool_policies",
        "control_published_agents",
    }
    assert _table_names(_sqlite_path(settings.data_plane_database_url)) >= {
        "data_trajectory",
        "data_trace_spans",
        "data_run_evaluations",
        "data_artifacts",
    }


def test_built_repositories_follow_rebuilt_store_after_reset_state() -> None:
    infrastructure = build_infrastructure()
    run = _run_record()

    infrastructure.run_repository.save(run)
    assert infrastructure.run_repository.get(run.run_id) == run

    reset_state()

    assert infrastructure.run_repository.get(run.run_id) is None
    replacement = _run_record()
    infrastructure.run_repository.save(replacement)
    assert infrastructure.run_repository.get(replacement.run_id) == replacement


def test_infrastructure_repositories_barrel_exposes_only_cross_cutting_helpers() -> None:
    assert not hasattr(infrastructure_repositories, "StateRunRepository")
    assert not hasattr(infrastructure_repositories, "StateDatasetRepository")
    assert not hasattr(infrastructure_repositories, "StatePublishedAgentRepository")
    assert hasattr(infrastructure_repositories, "StateSystemStatus")
    assert hasattr(infrastructure_repositories, "reset_state")
