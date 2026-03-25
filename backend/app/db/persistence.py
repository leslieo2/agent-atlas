from __future__ import annotations

import json
import sqlite3
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from threading import RLock
from typing import Any
from uuid import UUID

from app.core.config import settings
from app.modules.artifacts.domain.models import ArtifactMetadata
from app.modules.datasets.domain.models import Dataset
from app.modules.evals.domain.models import EvalJob
from app.modules.replays.domain.models import ReplayResult
from app.modules.runs.domain.models import RunRecord, TrajectoryStep
from app.modules.traces.domain.models import TraceSpan


def to_uuid(value: UUID | str) -> UUID:
    if isinstance(value, UUID):
        return value
    return UUID(value)


def serialize_model(model: Any) -> str:
    return json.dumps(model.model_dump(mode="json"), ensure_ascii=False)


class StatePersistence:
    def __init__(self, database_url: str | None) -> None:
        self._lock = RLock()
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

        with self._lock:
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
        with self._lock:
            self.conn.execute(
                f"INSERT OR REPLACE INTO {table} ({key_col}, payload, updated_at) VALUES (?, ?, ?)",
                (key_value, payload, ts),
            )
            self.conn.commit()

    def _fetch_payload(self, table: str, key_col: str, key_value: str) -> str | None:
        if not self.conn:
            return None
        with self._lock:
            row = self.conn.execute(
                f"SELECT payload FROM {table} WHERE {key_col} = ?",
                (key_value,),
            ).fetchone()
        if not row:
            return None
        return str(row["payload"])

    def _fetch_payloads(self, query: str, params: tuple[object, ...] = ()) -> list[str]:
        if not self.conn:
            return []
        with self._lock:
            rows = self.conn.execute(query, params).fetchall()
        return [str(row["payload"]) for row in rows]

    def save_run(self, run: RunRecord) -> None:
        self._upsert(
            "runs",
            "run_id",
            str(run.run_id),
            serialize_model(run),
            datetime.now(UTC).isoformat(),
        )

    def get_run(self, run_id: UUID | str) -> RunRecord | None:
        payload = self._fetch_payload("runs", "run_id", str(to_uuid(run_id)))
        if payload is None:
            return None
        return RunRecord.model_validate(json.loads(payload))

    def list_runs(self) -> list[RunRecord]:
        payloads = self._fetch_payloads("SELECT payload FROM runs ORDER BY updated_at DESC")
        return [RunRecord.model_validate(json.loads(payload)) for payload in payloads]

    def save_trajectory_step(self, step: TrajectoryStep, position: int) -> None:
        if not self.conn:
            return
        with self._lock:
            self.conn.execute(
                """
                INSERT INTO trajectory (run_id, step_id, position, payload)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(run_id, step_id) DO UPDATE SET
                    position = excluded.position,
                    payload = excluded.payload
                """,
                (str(step.run_id), step.id, position, serialize_model(step)),
            )
            self.conn.commit()

    def append_trajectory_step(self, step: TrajectoryStep) -> None:
        if not self.conn:
            return
        with self._lock:
            existing = self.conn.execute(
                """
                SELECT position FROM trajectory
                WHERE run_id = ? AND step_id = ?
                """,
                (str(step.run_id), step.id),
            ).fetchone()
            if existing:
                position = int(existing["position"])
            else:
                row = self.conn.execute(
                    """
                    SELECT COALESCE(MAX(position), -1) + 1 AS next_position
                    FROM trajectory
                    WHERE run_id = ?
                    """,
                    (str(step.run_id),),
                ).fetchone()
                position = int(row["next_position"]) if row else 0
            self.conn.execute(
                """
                INSERT INTO trajectory (run_id, step_id, position, payload)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(run_id, step_id) DO UPDATE SET
                    position = excluded.position,
                    payload = excluded.payload
                """,
                (str(step.run_id), step.id, position, serialize_model(step)),
            )
            self.conn.commit()

    def list_trajectory(self, run_id: UUID | str) -> list[TrajectoryStep]:
        payloads = self._fetch_payloads(
            """
            SELECT payload FROM trajectory
            WHERE run_id = ?
            ORDER BY position ASC
            """,
            (str(to_uuid(run_id)),),
        )
        return [TrajectoryStep.model_validate(json.loads(payload)) for payload in payloads]

    def persist_trajectory(self, run_id: UUID, steps: list[TrajectoryStep]) -> None:
        if not self.conn:
            return
        with self._lock:
            self.conn.execute("DELETE FROM trajectory WHERE run_id = ?", (str(run_id),))
            for position, step in enumerate(steps):
                self.conn.execute(
                    """
                    INSERT INTO trajectory (run_id, step_id, position, payload)
                    VALUES (?, ?, ?, ?)
                    """,
                    (str(run_id), step.id, position, serialize_model(step)),
                )
            self.conn.commit()

    def save_trace_span(self, span: TraceSpan, position: int) -> None:
        if not self.conn:
            return
        with self._lock:
            self.conn.execute(
                """
                INSERT INTO trace_spans (run_id, span_id, position, payload)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(run_id, span_id) DO UPDATE SET
                    position = excluded.position,
                    payload = excluded.payload
                """,
                (str(span.run_id), span.span_id, position, serialize_model(span)),
            )
            self.conn.commit()

    def append_trace_span(self, span: TraceSpan) -> None:
        if not self.conn:
            return
        with self._lock:
            existing = self.conn.execute(
                """
                SELECT position FROM trace_spans
                WHERE run_id = ? AND span_id = ?
                """,
                (str(span.run_id), span.span_id),
            ).fetchone()
            if existing:
                position = int(existing["position"])
            else:
                row = self.conn.execute(
                    """
                    SELECT COALESCE(MAX(position), -1) + 1 AS next_position
                    FROM trace_spans
                    WHERE run_id = ?
                    """,
                    (str(span.run_id),),
                ).fetchone()
                position = int(row["next_position"]) if row else 0
            self.conn.execute(
                """
                INSERT INTO trace_spans (run_id, span_id, position, payload)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(run_id, span_id) DO UPDATE SET
                    position = excluded.position,
                    payload = excluded.payload
                """,
                (str(span.run_id), span.span_id, position, serialize_model(span)),
            )
            self.conn.commit()

    def list_trace_spans(self, run_id: UUID | str) -> list[TraceSpan]:
        payloads = self._fetch_payloads(
            """
            SELECT payload FROM trace_spans
            WHERE run_id = ?
            ORDER BY position ASC
            """,
            (str(to_uuid(run_id)),),
        )
        return [TraceSpan.model_validate(json.loads(payload)) for payload in payloads]

    def persist_trace_spans(self, run_id: UUID, spans: list[TraceSpan]) -> None:
        if not self.conn:
            return
        with self._lock:
            self.conn.execute("DELETE FROM trace_spans WHERE run_id = ?", (str(run_id),))
            for position, span in enumerate(spans):
                self.conn.execute(
                    """
                    INSERT INTO trace_spans (run_id, span_id, position, payload)
                    VALUES (?, ?, ?, ?)
                    """,
                    (str(run_id), span.span_id, position, serialize_model(span)),
                )
            self.conn.commit()

    def save_dataset(self, dataset: Dataset) -> None:
        self._upsert(
            "datasets",
            "name",
            dataset.name,
            serialize_model(dataset),
            datetime.now(UTC).isoformat(),
        )

    def get_dataset(self, name: str) -> Dataset | None:
        payload = self._fetch_payload("datasets", "name", name)
        if payload is None:
            return None
        return Dataset.model_validate(json.loads(payload))

    def list_datasets(self) -> list[Dataset]:
        payloads = self._fetch_payloads("SELECT payload FROM datasets ORDER BY updated_at DESC")
        return [Dataset.model_validate(json.loads(payload)) for payload in payloads]

    def save_eval_job(self, job: EvalJob) -> None:
        self._upsert(
            "eval_jobs",
            "job_id",
            str(job.job_id),
            serialize_model(job),
            job.created_at.isoformat(),
        )

    def get_eval_job(self, job_id: UUID | str) -> EvalJob | None:
        payload = self._fetch_payload("eval_jobs", "job_id", str(to_uuid(job_id)))
        if payload is None:
            return None
        return EvalJob.model_validate(json.loads(payload))

    def save_replay(self, replay: ReplayResult) -> None:
        self._upsert(
            "replays",
            "replay_id",
            str(replay.replay_id),
            serialize_model(replay),
            replay.started_at.isoformat(),
        )

    def get_replay(self, replay_id: UUID | str) -> ReplayResult | None:
        payload = self._fetch_payload("replays", "replay_id", str(to_uuid(replay_id)))
        if payload is None:
            return None
        return ReplayResult.model_validate(json.loads(payload))

    def save_artifact(self, artifact: ArtifactMetadata) -> None:
        self._upsert(
            "artifacts",
            "artifact_id",
            str(artifact.artifact_id),
            serialize_model(artifact),
            artifact.created_at.isoformat(),
        )

    def get_artifact(self, artifact_id: UUID | str) -> ArtifactMetadata | None:
        payload = self._fetch_payload("artifacts", "artifact_id", str(to_uuid(artifact_id)))
        if payload is None:
            return None
        return ArtifactMetadata.model_validate(json.loads(payload))

    def load_state(self) -> dict[str, Any]:
        runs = {to_uuid(run.run_id): run for run in self.list_runs()}
        trajectory = defaultdict(list)
        trace_spans = defaultdict(list)
        for run_id in runs:
            trajectory[run_id] = self.list_trajectory(run_id)
            trace_spans[run_id] = self.list_trace_spans(run_id)
        datasets = {dataset.name: dataset for dataset in self.list_datasets()}

        eval_jobs: dict[UUID, EvalJob] = {}
        for payload in self._fetch_payloads("SELECT payload FROM eval_jobs ORDER BY updated_at DESC"):
            job = EvalJob.model_validate(json.loads(payload))
            eval_jobs[to_uuid(job.job_id)] = job

        replays: dict[UUID, ReplayResult] = {}
        for payload in self._fetch_payloads("SELECT payload FROM replays ORDER BY updated_at DESC"):
            replay = ReplayResult.model_validate(json.loads(payload))
            replays[to_uuid(replay.replay_id)] = replay

        artifacts: dict[UUID, ArtifactMetadata] = {}
        for payload in self._fetch_payloads("SELECT payload FROM artifacts ORDER BY updated_at DESC"):
            artifact = ArtifactMetadata.model_validate(json.loads(payload))
            artifacts[to_uuid(artifact.artifact_id)] = artifact

        return {
            "runs": runs,
            "trajectory": trajectory,
            "trace_spans": trace_spans,
            "datasets": datasets,
            "eval_jobs": eval_jobs,
            "replays": replays,
            "artifacts": artifacts,
        }

    def reset_all(self) -> None:
        if not self.conn:
            return
        with self._lock:
            self.conn.executescript(
                """
                DELETE FROM trace_spans;
                DELETE FROM trajectory;
                DELETE FROM runs;
                DELETE FROM datasets;
                DELETE FROM eval_jobs;
                DELETE FROM replays;
                DELETE FROM artifacts;
                """
            )
            self.conn.commit()


def build_state_persistence() -> StatePersistence:
    return StatePersistence(settings.database_url)
