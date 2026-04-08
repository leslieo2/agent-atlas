from __future__ import annotations

from uuid import UUID, uuid4

from app.execution.adapters.experiments import RunBackedExperimentRunQuery
from app.modules.datasets.domain.models import DatasetSample, DatasetVersion
from app.modules.experiments.domain.models import (
    ExperimentRecord,
    ExperimentRunDetail,
    ExperimentSpec,
    RunEvaluationRecord,
)
from app.modules.runs.domain.models import RunRecord
from app.modules.shared.domain.enums import CurationStatus, RunStatus, SampleJudgement
from app.modules.shared.domain.models import (
    EvaluatorConfig,
    ModelConfig,
    PromptConfig,
    ToolsetConfig,
    TracePointer,
)


class StubDatasetRepository:
    def __init__(self, dataset_version: DatasetVersion) -> None:
        self.dataset_version = dataset_version

    def get_version(self, dataset_version_id: str | UUID) -> DatasetVersion | None:
        if self.dataset_version.dataset_version_id == UUID(str(dataset_version_id)):
            return self.dataset_version
        return None


class StubRunRepository:
    def __init__(self, runs: list[RunRecord]) -> None:
        self.runs = runs

    def list(self) -> list[RunRecord]:
        return list(self.runs)


class StubRunEvaluationRepository:
    def __init__(self, records: list[RunEvaluationRecord]) -> None:
        self.records = records

    def list_for_experiment(self, experiment_id: str | UUID) -> list[RunEvaluationRecord]:
        experiment_uuid = UUID(str(experiment_id))
        return [record for record in self.records if record.experiment_id == experiment_uuid]


def test_run_backed_experiment_run_query_preserves_evaluation_precedence_and_trace_fallback() -> (
    None
):
    experiment_id = uuid4()
    dataset_version_id = uuid4()
    experiment = ExperimentRecord(
        experiment_id=experiment_id,
        name="candidate",
        dataset_name="support",
        dataset_version_id=dataset_version_id,
        published_agent_id="agent-1",
        spec=ExperimentSpec(
            dataset_version_id=dataset_version_id,
            published_agent_id="agent-1",
            model_settings=ModelConfig(model="gpt-5.4-mini"),
            prompt_config=PromptConfig(prompt_version="v1"),
            toolset_config=ToolsetConfig(),
            evaluator_config=EvaluatorConfig(),
        ),
    )
    dataset_version = DatasetVersion(
        dataset_version_id=dataset_version_id,
        dataset_name="support",
        rows=[
            DatasetSample(
                sample_id="sample-1",
                input="alpha",
                expected="A",
                tags=["shipping"],
                slice="shipping",
                source="crm",
                export_eligible=True,
            ),
            DatasetSample(
                sample_id="sample-2",
                input="beta",
                expected="B",
                tags=["returns"],
                slice="returns",
                source="crm",
                export_eligible=False,
            ),
        ],
    )
    earlier_run = RunRecord.model_construct(
        run_id=uuid4(),
        attempt_id=uuid4(),
        experiment_id=experiment_id,
        dataset_version_id=dataset_version_id,
        input_summary="beta summary",
        status=RunStatus.FAILED,
        project="candidate",
        dataset="support",
        dataset_sample_id="sample-2",
        agent_id="agent-1",
        model="gpt-5.4-mini",
        agent_type="openai-agents",
        tags=["candidate"],
        created_at=experiment.created_at,
        error_code="provider_error",
        error_message="runner failed",
        trace_pointer=TracePointer(
            backend="phoenix",
            trace_url=None,
            project_url="https://phoenix.example/project",
        ),
        latency_ms=7,
        tool_calls=2,
    )
    later_run = RunRecord.model_construct(
        run_id=uuid4(),
        attempt_id=uuid4(),
        experiment_id=experiment_id,
        dataset_version_id=dataset_version_id,
        input_summary="alpha summary",
        status=RunStatus.SUCCEEDED,
        project="candidate",
        dataset="support",
        dataset_sample_id="sample-1",
        agent_id="agent-1",
        model="gpt-5.4-mini",
        agent_type="openai-agents",
        tags=["candidate"],
        created_at=experiment.created_at.replace(microsecond=experiment.created_at.microsecond + 1),
        trace_pointer=TracePointer(
            backend="phoenix",
            trace_url="https://phoenix.example/trace",
            project_url="https://phoenix.example/project",
        ),
        latency_ms=3,
        tool_calls=1,
    )
    evaluation = RunEvaluationRecord(
        experiment_id=experiment_id,
        dataset_version_id=dataset_version_id,
        dataset_sample_id="sample-1",
        run_id=later_run.run_id,
        judgement=SampleJudgement.PASSED,
        input="eval input",
        expected="eval expected",
        actual="eval actual",
        trace_url=" https://phoenix.example/eval-trace ",
        tags=["eval-tag"],
        slice="eval-slice",
        source="eval-source",
        export_eligible=False,
        curation_status=CurationStatus.INCLUDE,
        curation_note="looks good",
        latency_ms=11,
        tool_calls=4,
        run_status=RunStatus.SUCCEEDED,
    )

    query = RunBackedExperimentRunQuery(
        dataset_repository=StubDatasetRepository(dataset_version),
        run_repository=StubRunRepository([later_run, earlier_run]),
        run_evaluation_repository=StubRunEvaluationRepository([evaluation]),
    )

    details = query.list_details(experiment)

    assert [detail.dataset_sample_id for detail in details] == ["sample-2", "sample-1"]

    first = details[0]
    assert isinstance(first, ExperimentRunDetail)
    assert first.input == "beta"
    assert first.expected == "B"
    assert first.tags == ["returns"]
    assert first.trace_url == "https://phoenix.example/project"
    assert first.error_code == "provider_error"

    second = details[1]
    assert second.input == "eval input"
    assert second.expected == "eval expected"
    assert second.actual == "eval actual"
    assert second.tags == ["eval-tag"]
    assert second.slice == "eval-slice"
    assert second.source == "eval-source"
    assert second.curation_status == CurationStatus.INCLUDE
    assert second.trace_url == "https://phoenix.example/eval-trace"
