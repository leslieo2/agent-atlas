from __future__ import annotations

import json
import sqlite3
from collections import defaultdict
from pathlib import Path
from threading import RLock
from typing import Any
from uuid import UUID

from app.core.config import settings
from app.models.schemas import (
    AdapterDescriptor,
    AdapterKind,
    ArtifactMetadata,
    Dataset,
    EvalJob,
    ReplayResult,
    RunRecord,
    TraceSpan,
    TrajectoryStep,
)


def _to_uuid(value: UUID | str) -> UUID:
    if isinstance(value, UUID):
        return value
    return UUID(value)


def _serialize_model(model: Any) -> str:
    return json.dumps(model.model_dump(mode="json"), ensure_ascii=False)


class _StatePersistence:
    def __init__(self, database_url: str | None) -> None:
        self.conn = self._connect(database_url)
        self.enabled = self.conn is not None
        self._init_schema()

    def _connect(self, database_url: str | None) -> sqlite3.Connection | None:
        if not database_url:
            default_path = (
                Path(__file__).resolve().parents[2] / "data" / "flight_recorder_state.db"
            ).resolve()
            database_url = f"sqlite:///{default_path}"
        database_url = database_url.strip()
        if not database_url.startswith("sqlite:///"):
            return None

        path = database_url[len("sqlite:///") :].strip()
        if not path or path == ":memory:":
            return None

        db_path = Path(path)
        if not db_path.is_absolute():
            db_path = Path.cwd() / db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL;")
        return conn

    def _init_schema(self) -> None:
        if not self.conn:
            return

        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS runs (
                run_id TEXT PRIMARY KEY,
                payload TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS trajectory (
                run_id TEXT NOT NULL,
                step_id TEXT NOT NULL,
                position INTEGER NOT NULL,
                payload TEXT NOT NULL,
                PRIMARY KEY (run_id, step_id),
                FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS trace_spans (
                run_id TEXT NOT NULL,
                span_id TEXT NOT NULL,
                position INTEGER NOT NULL,
                payload TEXT NOT NULL,
                PRIMARY KEY (run_id, span_id),
                FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS datasets (
                name TEXT PRIMARY KEY,
                payload TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS eval_jobs (
                job_id TEXT PRIMARY KEY,
                payload TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS replays (
                replay_id TEXT PRIMARY KEY,
                payload TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS artifacts (
                artifact_id TEXT PRIMARY KEY,
                payload TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )
        self.conn.commit()

    def _upsert(self, table: str, key_col: str, key_value: str, payload: str, ts: str) -> None:
        if not self.conn:
            return
        self.conn.execute(
            f"INSERT OR REPLACE INTO {table} ({key_col}, payload, updated_at) VALUES (?, ?, ?)",
            (key_value, payload, ts),
        )
        self.conn.commit()

    def save_run(self, run: RunRecord) -> None:
        from datetime import datetime

        self._upsert(
            "runs",
            "run_id",
            str(run.run_id),
            _serialize_model(run),
            datetime.utcnow().isoformat(),
        )

    def save_trajectory_step(self, step: TrajectoryStep, position: int) -> None:
        if not self.conn:
            return
        self.conn.execute(
            """
            INSERT INTO trajectory (run_id, step_id, position, payload)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(run_id, step_id) DO UPDATE SET
                position = excluded.position,
                payload = excluded.payload
            """,
            (str(step.run_id), step.id, position, _serialize_model(step)),
        )
        self.conn.commit()

    def persist_trajectory(self, run_id: UUID, steps: list[TrajectoryStep]) -> None:
        if not self.conn:
            return
        self.conn.execute("DELETE FROM trajectory WHERE run_id = ?", (str(run_id),))
        for position, step in enumerate(steps):
            self.conn.execute(
                """
                INSERT INTO trajectory (run_id, step_id, position, payload)
                VALUES (?, ?, ?, ?)
                """,
                (str(run_id), step.id, position, _serialize_model(step)),
            )
        self.conn.commit()

    def save_trace_span(self, span: TraceSpan, position: int) -> None:
        if not self.conn:
            return
        self.conn.execute(
            """
            INSERT INTO trace_spans (run_id, span_id, position, payload)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(run_id, span_id) DO UPDATE SET
                position = excluded.position,
                payload = excluded.payload
            """,
            (str(span.run_id), span.span_id, position, _serialize_model(span)),
        )
        self.conn.commit()

    def persist_trace_spans(self, run_id: UUID, spans: list[TraceSpan]) -> None:
        if not self.conn:
            return
        self.conn.execute("DELETE FROM trace_spans WHERE run_id = ?", (str(run_id),))
        for position, span in enumerate(spans):
            self.conn.execute(
                """
                INSERT INTO trace_spans (run_id, span_id, position, payload)
                VALUES (?, ?, ?, ?)
                """,
                (str(run_id), span.span_id, position, _serialize_model(span)),
            )
        self.conn.commit()

    def save_dataset(self, dataset: Dataset) -> None:
        from datetime import datetime

        self._upsert(
            "datasets",
            "name",
            dataset.name,
            _serialize_model(dataset),
            datetime.utcnow().isoformat(),
        )

    def save_eval_job(self, job: EvalJob) -> None:
        self._upsert(
            "eval_jobs",
            "job_id",
            str(job.job_id),
            _serialize_model(job),
            job.created_at.isoformat(),
        )

    def save_replay(self, replay: ReplayResult) -> None:
        if not self.conn:
            return
        ts = replay.started_at.isoformat()
        self.conn.execute(
            """
            INSERT OR REPLACE INTO replays (replay_id, payload, updated_at)
            VALUES (?, ?, ?)
            """,
            (str(replay.replay_id), _serialize_model(replay), ts),
        )
        self.conn.commit()

    def save_artifact(self, artifact: ArtifactMetadata) -> None:
        if not self.conn:
            return
        self.conn.execute(
            """
            INSERT OR REPLACE INTO artifacts (artifact_id, payload, updated_at)
            VALUES (?, ?, ?)
            """,
            (
                str(artifact.artifact_id),
                _serialize_model(artifact),
                artifact.created_at.isoformat(),
            ),
        )
        self.conn.commit()

    def load_state(self) -> dict[str, Any]:
        if not self.conn:
            return {
                "runs": {},
                "trajectory": defaultdict(list),
                "trace_spans": defaultdict(list),
                "datasets": {},
                "eval_jobs": {},
                "replays": {},
                "artifacts": {},
            }

        cursor = self.conn.cursor()
        runs: dict[UUID, RunRecord] = {}
        for row in cursor.execute("SELECT payload FROM runs"):
            payload = json.loads(row["payload"])
            run = RunRecord.model_validate(payload)
            runs[_to_uuid(run.run_id)] = run

        trajectory = defaultdict(list)
        for row in cursor.execute(
            """
            SELECT run_id, payload
            FROM trajectory
            ORDER BY run_id, position
            """
        ):
            payload = json.loads(row["payload"])
            step = TrajectoryStep.model_validate(payload)
            trajectory[_to_uuid(row["run_id"])].append(step)

        trace_spans = defaultdict(list)
        for row in cursor.execute(
            """
            SELECT run_id, payload
            FROM trace_spans
            ORDER BY run_id, position
            """
        ):
            payload = json.loads(row["payload"])
            span = TraceSpan.model_validate(payload)
            trace_spans[_to_uuid(row["run_id"])].append(span)

        datasets: dict[str, Dataset] = {}
        for row in cursor.execute("SELECT payload FROM datasets"):
            payload = json.loads(row["payload"])
            dataset = Dataset.model_validate(payload)
            datasets[dataset.name] = dataset

        eval_jobs: dict[UUID, EvalJob] = {}
        for row in cursor.execute("SELECT payload FROM eval_jobs"):
            payload = json.loads(row["payload"])
            job = EvalJob.model_validate(payload)
            eval_jobs[_to_uuid(job.job_id)] = job

        replays: dict[UUID, ReplayResult] = {}
        for row in cursor.execute("SELECT payload FROM replays"):
            payload = json.loads(row["payload"])
            replay = ReplayResult.model_validate(payload)
            replays[_to_uuid(replay.replay_id)] = replay

        artifacts: dict[UUID, ArtifactMetadata] = {}
        for row in cursor.execute("SELECT payload FROM artifacts"):
            payload = json.loads(row["payload"])
            artifact = ArtifactMetadata.model_validate(payload)
            artifacts[_to_uuid(artifact.artifact_id)] = artifact

        return {
            "runs": runs,
            "trajectory": trajectory,
            "trace_spans": trace_spans,
            "datasets": datasets,
            "eval_jobs": eval_jobs,
            "replays": replays,
            "artifacts": artifacts,
        }


class State:
    def __init__(self) -> None:
        self.lock = RLock()
        self.persist = _StatePersistence(settings.database_url)
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
        return _to_uuid(value)

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


state = State()
