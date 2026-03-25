from __future__ import annotations

import json
import sqlite3
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import UUID

from app.core.config import settings
from app.modules.artifacts.domain.models import ArtifactMetadata
from app.modules.datasets.domain.models import Dataset
from app.modules.evals.domain.models import EvalJob
from app.modules.replays.domain.models import ReplayResult
from app.modules.runs.domain.models import RunRecord, TrajectoryStep
from app.modules.shared.domain.tasks import QueuedTask, TaskStatus
from app.modules.traces.domain.models import TraceSpan


def to_uuid(value: UUID | str) -> UUID:
    if isinstance(value, UUID):
        return value
    return UUID(value)


def serialize_model(model: Any) -> str:
    return json.dumps(model.model_dump(mode="json"), ensure_ascii=False)


class StatePersistence:
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

            CREATE TABLE IF NOT EXISTS tasks (
                task_id TEXT PRIMARY KEY,
                task_type TEXT NOT NULL,
                target_id TEXT NOT NULL,
                payload TEXT NOT NULL,
                status TEXT NOT NULL,
                attempts INTEGER NOT NULL DEFAULT 0,
                error TEXT,
                claimed_by TEXT,
                claimed_at TEXT,
                created_at TEXT NOT NULL,
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
            serialize_model(run),
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
            (str(step.run_id), step.id, position, serialize_model(step)),
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
                (str(run_id), step.id, position, serialize_model(step)),
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
            (str(span.run_id), span.span_id, position, serialize_model(span)),
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
                (str(run_id), span.span_id, position, serialize_model(span)),
            )
        self.conn.commit()

    def save_dataset(self, dataset: Dataset) -> None:
        from datetime import datetime

        self._upsert(
            "datasets",
            "name",
            dataset.name,
            serialize_model(dataset),
            datetime.utcnow().isoformat(),
        )

    def save_eval_job(self, job: EvalJob) -> None:
        self._upsert(
            "eval_jobs",
            "job_id",
            str(job.job_id),
            serialize_model(job),
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
            (str(replay.replay_id), serialize_model(replay), ts),
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
                serialize_model(artifact),
                artifact.created_at.isoformat(),
            ),
        )
        self.conn.commit()

    def enqueue_task(self, task: QueuedTask) -> None:
        if not self.conn:
            raise RuntimeError("task queue requires sqlite persistence")
        self.conn.execute(
            """
            INSERT INTO tasks (
                task_id, task_type, target_id, payload, status, attempts, error,
                claimed_by, claimed_at, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(task.task_id),
                task.task_type.value,
                str(task.target_id),
                json.dumps(task.payload, ensure_ascii=False),
                task.status.value,
                task.attempts,
                task.error,
                task.claimed_by,
                task.claimed_at.isoformat() if task.claimed_at else None,
                task.created_at.isoformat(),
                task.updated_at.isoformat(),
            ),
        )
        self.conn.commit()

    def claim_next_task(self, worker_name: str, lease_seconds: int) -> QueuedTask | None:
        if not self.conn:
            raise RuntimeError("task queue requires sqlite persistence")

        now = datetime.utcnow()
        now_iso = now.isoformat()
        stale_before = (now - timedelta(seconds=max(1, lease_seconds))).isoformat()
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            row = self.conn.execute(
                """
                SELECT *
                FROM tasks
                WHERE status = ?
                   OR (status = ? AND claimed_at IS NOT NULL AND claimed_at <= ?)
                ORDER BY created_at ASC
                LIMIT 1
                """,
                (
                    TaskStatus.PENDING.value,
                    TaskStatus.RUNNING.value,
                    stale_before,
                ),
            ).fetchone()
            if row is None:
                self.conn.commit()
                return None

            self.conn.execute(
                """
                UPDATE tasks
                SET status = ?, attempts = attempts + 1, error = NULL,
                    claimed_by = ?, claimed_at = ?, updated_at = ?
                WHERE task_id = ?
                """,
                (
                    TaskStatus.RUNNING.value,
                    worker_name,
                    now_iso,
                    now_iso,
                    row["task_id"],
                ),
            )
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

        return self._task_from_row(
            {
                **dict(row),
                "status": TaskStatus.RUNNING.value,
                "attempts": int(row["attempts"]) + 1,
                "error": None,
                "claimed_by": worker_name,
                "claimed_at": now_iso,
                "updated_at": now_iso,
            }
        )

    def mark_task_done(self, task_id: UUID | str) -> None:
        self._update_task_status(task_id, TaskStatus.SUCCEEDED)

    def mark_task_failed(self, task_id: UUID | str, error: str) -> None:
        self._update_task_status(task_id, TaskStatus.FAILED, error=error)

    def reset(self) -> None:
        if not self.conn:
            return
        self.conn.executescript(
            """
            DELETE FROM trajectory;
            DELETE FROM trace_spans;
            DELETE FROM runs;
            DELETE FROM datasets;
            DELETE FROM eval_jobs;
            DELETE FROM replays;
            DELETE FROM artifacts;
            DELETE FROM tasks;
            """
        )
        self.conn.commit()

    def _update_task_status(
        self,
        task_id: UUID | str,
        status: TaskStatus,
        *,
        error: str | None = None,
    ) -> None:
        if not self.conn:
            raise RuntimeError("task queue requires sqlite persistence")
        self.conn.execute(
            """
            UPDATE tasks
            SET status = ?, error = ?, updated_at = ?
            WHERE task_id = ?
            """,
            (
                status.value,
                error,
                datetime.utcnow().isoformat(),
                str(to_uuid(task_id)),
            ),
        )
        self.conn.commit()

    @staticmethod
    def _task_from_row(row: sqlite3.Row | dict[str, Any]) -> QueuedTask:
        task_row = dict(row)
        return QueuedTask.model_validate(
            {
                "task_id": task_row["task_id"],
                "task_type": task_row["task_type"],
                "target_id": task_row["target_id"],
                "payload": json.loads(task_row["payload"]),
                "status": task_row["status"],
                "attempts": task_row["attempts"],
                "error": task_row["error"],
                "claimed_by": task_row["claimed_by"],
                "claimed_at": task_row["claimed_at"],
                "created_at": task_row["created_at"],
                "updated_at": task_row["updated_at"],
            }
        )

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
            run = RunRecord.model_validate(json.loads(row["payload"]))
            runs[to_uuid(run.run_id)] = run

        trajectory = defaultdict(list)
        for row in cursor.execute(
            """
            SELECT run_id, payload
            FROM trajectory
            ORDER BY run_id, position
            """
        ):
            step = TrajectoryStep.model_validate(json.loads(row["payload"]))
            trajectory[to_uuid(row["run_id"])].append(step)

        trace_spans = defaultdict(list)
        for row in cursor.execute(
            """
            SELECT run_id, payload
            FROM trace_spans
            ORDER BY run_id, position
            """
        ):
            span = TraceSpan.model_validate(json.loads(row["payload"]))
            trace_spans[to_uuid(row["run_id"])].append(span)

        datasets: dict[str, Dataset] = {}
        for row in cursor.execute("SELECT payload FROM datasets"):
            dataset = Dataset.model_validate(json.loads(row["payload"]))
            datasets[dataset.name] = dataset

        eval_jobs: dict[UUID, EvalJob] = {}
        for row in cursor.execute("SELECT payload FROM eval_jobs"):
            job = EvalJob.model_validate(json.loads(row["payload"]))
            eval_jobs[to_uuid(job.job_id)] = job

        replays: dict[UUID, ReplayResult] = {}
        for row in cursor.execute("SELECT payload FROM replays"):
            replay = ReplayResult.model_validate(json.loads(row["payload"]))
            replays[to_uuid(replay.replay_id)] = replay

        artifacts: dict[UUID, ArtifactMetadata] = {}
        for row in cursor.execute("SELECT payload FROM artifacts"):
            artifact = ArtifactMetadata.model_validate(json.loads(row["payload"]))
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


def build_state_persistence() -> StatePersistence:
    return StatePersistence(settings.database_url)
