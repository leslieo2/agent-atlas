from __future__ import annotations

from threading import RLock
from uuid import UUID

from app.db.persistence import StatePersistence, to_uuid
from app.modules.adapters.domain.models import AdapterDescriptor
from app.modules.artifacts.domain.models import ArtifactMetadata
from app.modules.datasets.domain.models import Dataset
from app.modules.evals.domain.models import EvalJob
from app.modules.replays.domain.models import ReplayResult
from app.modules.runs.domain.models import RunRecord, TrajectoryStep
from app.modules.shared.domain.enums import AdapterKind
from app.modules.traces.domain.models import TraceSpan


class StateStore:
    def __init__(self, persistence: StatePersistence) -> None:
        self.lock = RLock()
        self.persist = persistence
        loaded = self.persist.load_state()
        self.runs: dict[UUID, RunRecord] = loaded["runs"]
        self.trajectory: dict[UUID, list[TrajectoryStep]] = loaded["trajectory"]
        self.trace_spans: dict[UUID, list[TraceSpan]] = loaded["trace_spans"]
        self.datasets: dict[str, Dataset] = loaded["datasets"]
        self.eval_jobs: dict[UUID, EvalJob] = loaded["eval_jobs"]
        self.replays: dict[UUID, ReplayResult] = loaded["replays"]
        self.artifacts: dict[UUID, ArtifactMetadata] = loaded["artifacts"]
        self.adapters = [
            AdapterDescriptor(
                kind=AdapterKind.OPENAI_AGENTS,
                name="OpenAI Agents SDK",
                runtime_version="stable",
                notes="In-memory runtime adapter with OpenAI-compatible traces",
                supports_replay=True,
                supports_eval=True,
            ),
            AdapterDescriptor(
                kind=AdapterKind.LANGCHAIN,
                name="LangChain",
                runtime_version="stable",
                notes="LangChain ChatOpenAI runtime bridge",
                supports_replay=True,
                supports_eval=True,
            ),
            AdapterDescriptor(
                kind=AdapterKind.MCP,
                name="MCP Tool Shim",
                runtime_version="v1",
                notes="Tool integration facade for external MCP servers",
                supports_replay=False,
                supports_eval=False,
            ),
        ]
        self.seeded = bool(self.datasets)

    def copy_trajectory(self, run_id: UUID) -> list[TrajectoryStep]:
        return list(self.trajectory.get(run_id, []))

    def copy_trace_spans(self, run_id: UUID) -> list[TraceSpan]:
        return list(self.trace_spans.get(run_id, []))

    @staticmethod
    def _coerce_uuid(value: UUID | str) -> UUID:
        return to_uuid(value)

    def save_run(self, run: RunRecord) -> None:
        with self.lock:
            self.runs[run.run_id] = run
            self.persist.save_run(run)

    def append_trajectory_step(self, step: TrajectoryStep) -> None:
        with self.lock:
            steps = self.trajectory.setdefault(step.run_id, [])
            existing_index = None
            for index, item in enumerate(steps):
                if item.id == step.id:
                    existing_index = index
                    break
            if existing_index is None:
                steps.append(step)
                position = len(steps) - 1
            else:
                steps[existing_index] = step
                position = existing_index
            self.persist.save_trajectory_step(step, position)

    def persist_trajectory(self, run_id: UUID | str) -> None:
        run_id = self._coerce_uuid(run_id)
        with self.lock:
            self.persist.persist_trajectory(run_id, list(self.trajectory.get(run_id, [])))

    def append_trace_span(self, span: TraceSpan) -> None:
        with self.lock:
            spans = self.trace_spans.setdefault(span.run_id, [])
            existing_index = None
            for index, item in enumerate(spans):
                if item.span_id == span.span_id:
                    existing_index = index
                    break
            if existing_index is None:
                spans.append(span)
                position = len(spans) - 1
            else:
                spans[existing_index] = span
                position = existing_index
            self.persist.save_trace_span(span, position)

    def persist_trace_spans(self, run_id: UUID | str) -> None:
        run_id = self._coerce_uuid(run_id)
        with self.lock:
            self.persist.persist_trace_spans(run_id, list(self.trace_spans.get(run_id, [])))

    def save_dataset(self, dataset: Dataset) -> None:
        with self.lock:
            self.datasets[dataset.name] = dataset
            self.persist.save_dataset(dataset)

    def save_eval_job(self, job: EvalJob) -> None:
        with self.lock:
            self.eval_jobs[job.job_id] = job
            self.persist.save_eval_job(job)

    def save_replay(self, replay: ReplayResult) -> None:
        with self.lock:
            self.replays[replay.replay_id] = replay
            self.persist.save_replay(replay)

    def save_artifact(self, artifact: ArtifactMetadata) -> None:
        with self.lock:
            self.artifacts[artifact.artifact_id] = artifact
            self.persist.save_artifact(artifact)
