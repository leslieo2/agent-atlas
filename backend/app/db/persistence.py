from __future__ import annotations

import json
import sqlite3
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import RLock
from typing import Any
from uuid import UUID

from app.core.config import settings
from app.modules.agents.domain.models import PublishedAgent
from app.modules.artifacts.domain.models import ArtifactMetadata
from app.modules.datasets.domain.models import Dataset
from app.modules.evals.domain.models import EvalJobRecord, EvalSampleResult
from app.modules.runs.domain.models import RunRecord, TrajectoryStep
from app.modules.shared.domain.tasks import QueuedTask, TaskStatus
from app.modules.traces.domain.models import TraceSpan

_PAYLOAD_STATEMENTS: dict[tuple[str, str], tuple[str, str]] = {
    (
        "runs",
        "run_id",
    ): (
        "INSERT OR REPLACE INTO runs (run_id, payload, updated_at) VALUES (?, ?, ?)",
        "SELECT payload FROM runs WHERE run_id = ?",
    ),
    (
        "eval_jobs",
        "eval_job_id",
    ): (
        "INSERT OR REPLACE INTO eval_jobs (eval_job_id, payload, updated_at) VALUES (?, ?, ?)",
        "SELECT payload FROM eval_jobs WHERE eval_job_id = ?",
    ),
    (
        "datasets",
        "name",
    ): (
        "INSERT OR REPLACE INTO datasets (name, payload, updated_at) VALUES (?, ?, ?)",
        "SELECT payload FROM datasets WHERE name = ?",
    ),
    (
        "artifacts",
        "artifact_id",
    ): (
        "INSERT OR REPLACE INTO artifacts (artifact_id, payload, updated_at) VALUES (?, ?, ?)",
        "SELECT payload FROM artifacts WHERE artifact_id = ?",
    ),
    (
        "published_agents",
        "agent_id",
    ): (
        (
            "INSERT OR REPLACE INTO published_agents (agent_id, payload, updated_at) "
            "VALUES (?, ?, ?)"
        ),
        "SELECT payload FROM published_agents WHERE agent_id = ?",
    ),
}


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
                    eval_job_id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS eval_sample_results (
                    eval_job_id TEXT NOT NULL,
                    dataset_sample_id TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (eval_job_id, dataset_sample_id),
                    FOREIGN KEY (eval_job_id) REFERENCES eval_jobs(eval_job_id) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS artifacts (
                    artifact_id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS published_agents (
                    agent_id TEXT PRIMARY KEY,
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
            self._ensure_eval_table_schema()
            self.conn.commit()

    def _ensure_eval_table_schema(self) -> None:
        if not self.conn:
            return

        expected_columns = {
            "eval_jobs": {"eval_job_id", "payload", "updated_at"},
            "eval_sample_results": {
                "eval_job_id",
                "dataset_sample_id",
                "payload",
                "updated_at",
            },
        }

        for table_name, required_columns in expected_columns.items():
            rows = self.conn.execute(f"PRAGMA table_info({table_name})").fetchall()
            existing_columns = {str(row["name"]) for row in rows}
            if rows and not required_columns.issubset(existing_columns):
                self.conn.execute(f"DROP TABLE IF EXISTS {table_name}")

        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS eval_jobs (
                eval_job_id TEXT PRIMARY KEY,
                payload TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS eval_sample_results (
                eval_job_id TEXT NOT NULL,
                dataset_sample_id TEXT NOT NULL,
                payload TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (eval_job_id, dataset_sample_id),
                FOREIGN KEY (eval_job_id) REFERENCES eval_jobs(eval_job_id) ON DELETE CASCADE
            );
            """
        )

    def _upsert(self, table: str, key_col: str, key_value: str, payload: str, ts: str) -> None:
        if not self.conn:
            return
        statement = self._payload_statement(table, key_col, kind="upsert")
        with self._lock:
            self.conn.execute(statement, (key_value, payload, ts))
            self.conn.commit()

    def _fetch_payload(self, table: str, key_col: str, key_value: str) -> str | None:
        if not self.conn:
            return None
        statement = self._payload_statement(table, key_col, kind="fetch")
        with self._lock:
            row = self.conn.execute(statement, (key_value,)).fetchone()
        if not row:
            return None
        return str(row["payload"])

    def _fetch_payloads(self, query: str, params: tuple[object, ...] = ()) -> list[str]:
        if not self.conn:
            return []
        with self._lock:
            rows = self.conn.execute(query, params).fetchall()
        return [str(row["payload"]) for row in rows]

    def _payload_statement(self, table: str, key_col: str, *, kind: str) -> str:
        statements = _PAYLOAD_STATEMENTS.get((table, key_col))
        if statements is None:
            raise ValueError(f"unsupported payload table lookup table={table} key_col={key_col}")
        return statements[0] if kind == "upsert" else statements[1]

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

    def save_published_agent(self, agent: PublishedAgent) -> None:
        self._upsert(
            "published_agents",
            "agent_id",
            agent.agent_id,
            serialize_model(agent),
            datetime.now(UTC).isoformat(),
        )

    def get_published_agent(self, agent_id: str) -> PublishedAgent | None:
        payload = self._fetch_payload("published_agents", "agent_id", agent_id)
        if payload is None:
            return None
        return PublishedAgent.model_validate(json.loads(payload))

    def list_published_agents(self) -> list[PublishedAgent]:
        payloads = self._fetch_payloads(
            "SELECT payload FROM published_agents ORDER BY updated_at DESC"
        )
        return [PublishedAgent.model_validate(json.loads(payload)) for payload in payloads]

    def delete_published_agent(self, agent_id: str) -> bool:
        if not self.conn:
            return False
        with self._lock:
            cursor = self.conn.execute(
                "DELETE FROM published_agents WHERE agent_id = ?",
                (agent_id,),
            )
            self.conn.commit()
        return bool(cursor.rowcount)

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

    def save_eval_job(self, job: EvalJobRecord) -> None:
        self._upsert(
            "eval_jobs",
            "eval_job_id",
            str(job.eval_job_id),
            serialize_model(job),
            datetime.now(UTC).isoformat(),
        )

    def get_eval_job(self, eval_job_id: UUID | str) -> EvalJobRecord | None:
        payload = self._fetch_payload("eval_jobs", "eval_job_id", str(to_uuid(eval_job_id)))
        if payload is None:
            return None
        return EvalJobRecord.model_validate(json.loads(payload))

    def list_eval_jobs(self) -> list[EvalJobRecord]:
        payloads = self._fetch_payloads("SELECT payload FROM eval_jobs ORDER BY updated_at DESC")
        return [EvalJobRecord.model_validate(json.loads(payload)) for payload in payloads]

    def save_eval_sample_result(self, result: EvalSampleResult) -> None:
        if not self.conn:
            return
        with self._lock:
            self.conn.execute(
                """
                INSERT INTO eval_sample_results (
                    eval_job_id, dataset_sample_id, payload, updated_at
                )
                VALUES (?, ?, ?, ?)
                ON CONFLICT(eval_job_id, dataset_sample_id) DO UPDATE SET
                    payload = excluded.payload,
                    updated_at = excluded.updated_at
                """,
                (
                    str(result.eval_job_id),
                    result.dataset_sample_id,
                    serialize_model(result),
                    datetime.now(UTC).isoformat(),
                ),
            )
            self.conn.commit()

    def list_eval_sample_results(self, eval_job_id: UUID | str) -> list[EvalSampleResult]:
        payloads = self._fetch_payloads(
            """
            SELECT payload FROM eval_sample_results
            WHERE eval_job_id = ?
            ORDER BY dataset_sample_id ASC
            """,
            (str(to_uuid(eval_job_id)),),
        )
        return [EvalSampleResult.model_validate(json.loads(payload)) for payload in payloads]

    def get_eval_sample_result(
        self,
        eval_job_id: UUID | str,
        dataset_sample_id: str,
    ) -> EvalSampleResult | None:
        payloads = self._fetch_payloads(
            """
            SELECT payload FROM eval_sample_results
            WHERE eval_job_id = ? AND dataset_sample_id = ?
            LIMIT 1
            """,
            (str(to_uuid(eval_job_id)), dataset_sample_id),
        )
        if not payloads:
            return None
        return EvalSampleResult.model_validate(json.loads(payloads[0]))

    def delete_eval_sample_results(self, eval_job_id: UUID | str) -> None:
        if not self.conn:
            return
        with self._lock:
            self.conn.execute(
                "DELETE FROM eval_sample_results WHERE eval_job_id = ?",
                (str(to_uuid(eval_job_id)),),
            )
            self.conn.commit()

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

    def list_artifacts(self) -> list[ArtifactMetadata]:
        payloads = self._fetch_payloads("SELECT payload FROM artifacts ORDER BY updated_at DESC")
        return [ArtifactMetadata.model_validate(json.loads(payload)) for payload in payloads]

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

        now = datetime.now(UTC)
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
            DELETE FROM eval_sample_results;
            DELETE FROM eval_jobs;
            DELETE FROM artifacts;
            DELETE FROM published_agents;
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
                datetime.now(UTC).isoformat(),
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
        runs = {to_uuid(run.run_id): run for run in self.list_runs()}
        trajectory = defaultdict(list)
        trace_spans = defaultdict(list)
        for run_id in runs:
            trajectory[run_id] = self.list_trajectory(run_id)
            trace_spans[run_id] = self.list_trace_spans(run_id)
        datasets = {dataset.name: dataset for dataset in self.list_datasets()}

        artifacts: dict[UUID, ArtifactMetadata] = {}
        artifact_payloads = self._fetch_payloads(
            "SELECT payload FROM artifacts ORDER BY updated_at DESC"
        )
        for payload in artifact_payloads:
            artifact = ArtifactMetadata.model_validate(json.loads(payload))
            artifacts[to_uuid(artifact.artifact_id)] = artifact

        return {
            "runs": runs,
            "trajectory": trajectory,
            "trace_spans": trace_spans,
            "datasets": datasets,
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
                DELETE FROM eval_sample_results;
                DELETE FROM eval_jobs;
                DELETE FROM artifacts;
                DELETE FROM published_agents;
                """
            )
            self.conn.commit()


def build_state_persistence() -> StatePersistence:
    return StatePersistence(settings.database_url)
