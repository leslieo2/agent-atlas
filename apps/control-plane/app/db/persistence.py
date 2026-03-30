from __future__ import annotations

import json
import re
import sqlite3
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import RLock
from typing import Any, Literal
from uuid import UUID

from app.core.config import settings
from app.modules.agents.domain.models import PublishedAgent
from app.modules.datasets.domain.models import Dataset, DatasetVersion
from app.modules.experiments.domain.models import ExperimentRecord, RunEvaluationRecord
from app.modules.exports.domain.models import ArtifactMetadata
from app.modules.policies.domain.models import ApprovalPolicyRecord
from app.modules.runs.domain.models import RunRecord
from app.modules.shared.domain.models import TrajectoryStepRecord
from app.modules.shared.domain.tasks import QueuedTask, TaskStatus
from app.modules.shared.domain.traces import TraceSpan

_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def to_uuid(value: UUID | str) -> UUID:
    if isinstance(value, UUID):
        return value
    return UUID(value)


def serialize_model(model: Any) -> str:
    return json.dumps(model.model_dump(mode="json"), ensure_ascii=False)


def _normalize_experiment_payload(payload: dict[str, Any]) -> dict[str, Any]:
    spec = payload.get("spec")
    if isinstance(spec, dict) and "model_config" not in spec and "model_settings" in spec:
        spec["model_config"] = spec.pop("model_settings")
    return payload


def _validate_identifier(identifier: str) -> str:
    if not _IDENTIFIER_RE.fullmatch(identifier):
        raise ValueError(f"invalid SQL identifier '{identifier}'")
    return identifier


@dataclass(frozen=True)
class _PlaneConfig:
    name: Literal["control", "data"]
    database_url: str | None
    default_sqlite_path: Path
    postgres_schema: str
    sqlite_prefix: str


class _PlaneStore:
    def __init__(self, config: _PlaneConfig) -> None:
        self._lock = RLock()
        self.name = config.name
        self.database_url = self._resolve_database_url(
            database_url=config.database_url,
            default_sqlite_path=config.default_sqlite_path,
        )
        self.backend: Literal["sqlite", "postgres"]
        self.schema: str | None = None
        self.table_prefix = config.sqlite_prefix
        self.conn: Any = self._connect(self.database_url)
        self.enabled = self.conn is not None
        if self.backend == "postgres":
            self.schema = _validate_identifier(config.postgres_schema)
            self.table_prefix = ""

    @staticmethod
    def _resolve_database_url(database_url: str | None, default_sqlite_path: Path) -> str:
        if database_url and database_url.strip():
            return database_url.strip()
        default_sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{default_sqlite_path}"

    def _connect(self, database_url: str) -> sqlite3.Connection | Any:
        normalized = database_url.strip()
        if normalized.startswith("sqlite:///"):
            self.backend = "sqlite"
            path = normalized[len("sqlite:///") :].strip()
            if not path:
                raise RuntimeError(f"{self.name} plane database URL is missing a sqlite path")

            if path == ":memory:":
                conn = sqlite3.connect(":memory:", check_same_thread=False)
            else:
                db_path = Path(path)
                if not db_path.is_absolute():
                    db_path = Path.cwd() / db_path
                db_path.parent.mkdir(parents=True, exist_ok=True)
                conn = sqlite3.connect(db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON;")
            conn.execute("PRAGMA journal_mode = WAL;")
            return conn

        if normalized.startswith("postgresql://") or normalized.startswith("postgres://"):
            self.backend = "postgres"
            try:
                import psycopg
                from psycopg.rows import dict_row
            except ImportError as exc:  # pragma: no cover - exercised only with postgres URLs
                raise RuntimeError(
                    "PostgreSQL storage requires psycopg. Install backend dependencies first."
                ) from exc
            return psycopg.connect(normalized, autocommit=True, row_factory=dict_row)

        raise RuntimeError(
            f"unsupported database URL for {self.name} plane: "
            f"expected sqlite:/// or postgresql://, got '{normalized}'"
        )

    @property
    def placeholder(self) -> str:
        return "?" if self.backend == "sqlite" else "%s"

    def table(self, table_name: str) -> str:
        _validate_identifier(table_name)
        if self.backend == "postgres":
            if self.schema is None:
                return table_name
            return f"{self.schema}.{table_name}"
        return f"{self.table_prefix}{table_name}"

    def create_schema(self) -> None:
        if not self.conn or self.backend != "postgres" or self.schema is None:
            return
        self.execute(f"CREATE SCHEMA IF NOT EXISTS {self.schema}", commit=True)

    def execute(
        self,
        query: str,
        params: tuple[object, ...] = (),
        *,
        commit: bool = False,
    ) -> Any:
        with self._lock:
            cursor = self.conn.cursor()
            cursor.execute(query, params)
            if commit and self.backend == "sqlite":
                self.conn.commit()
            return cursor

    def fetchone(
        self,
        query: str,
        params: tuple[object, ...] = (),
    ) -> dict[str, Any] | None:
        with self._lock:
            cursor = self.conn.cursor()
            cursor.execute(query, params)
            row = cursor.fetchone()
        return self._row_to_dict(row)

    def fetchall(
        self,
        query: str,
        params: tuple[object, ...] = (),
    ) -> list[dict[str, Any]]:
        with self._lock:
            cursor = self.conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
        mapped_rows = [self._row_to_dict(row) for row in rows]
        return [row for row in mapped_rows if row is not None]

    def delete_all(self, tables: list[str]) -> None:
        if not self.conn:
            return
        with self._lock:
            cursor = self.conn.cursor()
            for table_name in tables:
                cursor.execute(f"DELETE FROM {self.table(table_name)}")  # nosec B608
            if self.backend == "sqlite":
                self.conn.commit()

    def close(self) -> None:
        if not self.conn:
            return
        with self._lock:
            self.conn.close()
            self.conn = None

    def claim_next_task(self, worker_name: str, lease_seconds: int) -> dict[str, Any] | None:
        tasks_table = self.table("tasks")
        now = datetime.now(UTC)
        now_iso = now.isoformat()
        stale_before = (now - timedelta(seconds=max(1, lease_seconds))).isoformat()
        pending = TaskStatus.PENDING.value
        running = TaskStatus.RUNNING.value

        if self.backend == "postgres":
            with self._lock:
                with self.conn.transaction():
                    cursor = self.conn.cursor()
                    cursor.execute(  # nosec B608
                        f"""
                        SELECT *
                        FROM {tasks_table}
                        WHERE status = {self.placeholder}
                           OR (
                               status = {self.placeholder}
                               AND claimed_at IS NOT NULL
                               AND claimed_at <= {self.placeholder}
                           )
                        ORDER BY created_at ASC
                        LIMIT 1
                        FOR UPDATE SKIP LOCKED
                        """,
                        (pending, running, stale_before),
                    )
                    row = cursor.fetchone()
                    if row is None:
                        return None

                    row_dict = self._row_to_dict(row)
                    if row_dict is None:
                        return None
                    cursor.execute(  # nosec B608
                        f"""
                        UPDATE {tasks_table}
                        SET status = {self.placeholder},
                            attempts = attempts + 1,
                            error = NULL,
                            claimed_by = {self.placeholder},
                            claimed_at = {self.placeholder},
                            updated_at = {self.placeholder}
                        WHERE task_id = {self.placeholder}
                        """,
                        (
                            TaskStatus.RUNNING.value,
                            worker_name,
                            now_iso,
                            now_iso,
                            row_dict["task_id"],
                        ),
                    )
                return {
                    **row_dict,
                    "status": TaskStatus.RUNNING.value,
                    "attempts": int(row_dict["attempts"]) + 1,
                    "error": None,
                    "claimed_by": worker_name,
                    "claimed_at": now_iso,
                    "updated_at": now_iso,
                }

        with self._lock:
            self.conn.execute("BEGIN IMMEDIATE")
            try:
                cursor = self.conn.cursor()
                cursor.execute(  # nosec B608
                    f"""
                    SELECT *
                    FROM {tasks_table}
                    WHERE status = {self.placeholder}
                       OR (
                           status = {self.placeholder}
                           AND claimed_at IS NOT NULL
                           AND claimed_at <= {self.placeholder}
                       )
                    ORDER BY created_at ASC
                    LIMIT 1
                    """,
                    (pending, running, stale_before),
                )
                row = cursor.fetchone()
                if row is None:
                    self.conn.commit()
                    return None

                row_dict = self._row_to_dict(row)
                if row_dict is None:
                    self.conn.commit()
                    return None
                cursor.execute(  # nosec B608
                    f"""
                    UPDATE {tasks_table}
                    SET status = {self.placeholder},
                        attempts = attempts + 1,
                        error = NULL,
                        claimed_by = {self.placeholder},
                        claimed_at = {self.placeholder},
                        updated_at = {self.placeholder}
                    WHERE task_id = {self.placeholder}
                    """,
                    (
                        TaskStatus.RUNNING.value,
                        worker_name,
                        now_iso,
                        now_iso,
                        row_dict["task_id"],
                    ),
                )
                self.conn.commit()
            except Exception:
                self.conn.rollback()
                raise

        return {
            **row_dict,
            "status": TaskStatus.RUNNING.value,
            "attempts": int(row_dict["attempts"]) + 1,
            "error": None,
            "claimed_by": worker_name,
            "claimed_at": now_iso,
            "updated_at": now_iso,
        }

    @staticmethod
    def _row_to_dict(row: Any) -> dict[str, Any] | None:
        if row is None:
            return None
        if isinstance(row, dict):
            return dict(row)
        return dict(row)


class StatePersistence:
    def __init__(
        self,
        control_database_url: str | None = None,
        data_database_url: str | None = None,
        *,
        control_schema: str = "control_plane",
        data_schema: str = "data_plane",
    ) -> None:
        base_dir = Path(__file__).resolve().parents[2] / "data"
        self._control = _PlaneStore(
            _PlaneConfig(
                name="control",
                database_url=control_database_url,
                default_sqlite_path=(base_dir / "control-plane-state.db").resolve(),
                postgres_schema=control_schema,
                sqlite_prefix="control_",
            )
        )
        self._data = _PlaneStore(
            _PlaneConfig(
                name="data",
                database_url=data_database_url,
                default_sqlite_path=(base_dir / "data-plane-state.db").resolve(),
                postgres_schema=data_schema,
                sqlite_prefix="data_",
            )
        )
        self.enabled = self._control.enabled and self._data.enabled
        self._init_schema()

    def _init_schema(self) -> None:
        self._control.create_schema()
        self._data.create_schema()
        self._init_control_schema()
        self._init_data_schema()

    def _init_control_schema(self) -> None:
        runs = self._control.table("runs")
        datasets = self._control.table("datasets")
        dataset_versions = self._control.table("dataset_versions")
        experiments = self._control.table("experiments")
        approval_policies = self._control.table("approval_policies")
        tool_policies = self._control.table("tool_policies")
        published_agents = self._control.table("published_agents")
        tasks = self._control.table("tasks")

        statements = [
            f"""
            CREATE TABLE IF NOT EXISTS {runs} (
                run_id TEXT PRIMARY KEY,
                payload TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """,
            f"""
            CREATE TABLE IF NOT EXISTS {datasets} (
                name TEXT PRIMARY KEY,
                payload TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """,
            f"""
            CREATE TABLE IF NOT EXISTS {dataset_versions} (
                dataset_version_id TEXT PRIMARY KEY,
                dataset_name TEXT NOT NULL,
                payload TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """,
            f"""
            CREATE TABLE IF NOT EXISTS {experiments} (
                experiment_id TEXT PRIMARY KEY,
                payload TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """,
            f"""
            CREATE TABLE IF NOT EXISTS {approval_policies} (
                approval_policy_id TEXT PRIMARY KEY,
                payload TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """,
            f"""
            CREATE TABLE IF NOT EXISTS {tool_policies} (
                approval_policy_id TEXT NOT NULL,
                tool_name TEXT NOT NULL,
                payload TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (approval_policy_id, tool_name)
            )
            """,
            f"""
            CREATE TABLE IF NOT EXISTS {published_agents} (
                agent_id TEXT PRIMARY KEY,
                payload TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """,
            f"""
            CREATE TABLE IF NOT EXISTS {tasks} (
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
            )
            """,
        ]

        for statement in statements:
            self._control.execute(statement, commit=True)

    def _init_data_schema(self) -> None:
        trajectory = self._data.table("trajectory")
        trace_spans = self._data.table("trace_spans")
        run_evaluations = self._data.table("run_evaluations")
        artifacts = self._data.table("artifacts")

        statements = [
            f"""
            CREATE TABLE IF NOT EXISTS {trajectory} (
                run_id TEXT NOT NULL,
                step_id TEXT NOT NULL,
                position INTEGER NOT NULL,
                payload TEXT NOT NULL,
                PRIMARY KEY (run_id, step_id)
            )
            """,
            f"""
            CREATE TABLE IF NOT EXISTS {trace_spans} (
                run_id TEXT NOT NULL,
                span_id TEXT NOT NULL,
                position INTEGER NOT NULL,
                payload TEXT NOT NULL,
                PRIMARY KEY (run_id, span_id)
            )
            """,
            f"""
            CREATE TABLE IF NOT EXISTS {run_evaluations} (
                run_id TEXT PRIMARY KEY,
                experiment_id TEXT NOT NULL,
                dataset_sample_id TEXT NOT NULL,
                payload TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """,
            f"""
            CREATE TABLE IF NOT EXISTS {artifacts} (
                artifact_id TEXT PRIMARY KEY,
                payload TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """,
        ]

        for statement in statements:
            self._data.execute(statement, commit=True)

    def _upsert_payload(
        self,
        store: _PlaneStore,
        *,
        table: str,
        key_col: str,
        key_value: str,
        payload: str,
        updated_at: str,
    ) -> None:
        placeholder = store.placeholder
        store.execute(  # nosec B608
            f"""
            INSERT INTO {store.table(table)} ({key_col}, payload, updated_at)
            VALUES ({placeholder}, {placeholder}, {placeholder})
            ON CONFLICT({key_col}) DO UPDATE SET
                payload = excluded.payload,
                updated_at = excluded.updated_at
            """,
            (key_value, payload, updated_at),
            commit=True,
        )

    def _fetch_payload(
        self,
        store: _PlaneStore,
        *,
        table: str,
        key_col: str,
        key_value: str,
    ) -> str | None:
        row = store.fetchone(  # nosec B608
            f"""
            SELECT payload
            FROM {store.table(table)}
            WHERE {key_col} = {store.placeholder}
            LIMIT 1
            """,
            (key_value,),
        )
        if row is None:
            return None
        return str(row["payload"])

    def _fetch_payloads(
        self,
        store: _PlaneStore,
        query: str,
        params: tuple[object, ...] = (),
    ) -> list[str]:
        rows = store.fetchall(query, params)
        return [str(row["payload"]) for row in rows]

    def save_run(self, run: RunRecord) -> None:
        self._upsert_payload(
            self._control,
            table="runs",
            key_col="run_id",
            key_value=str(run.run_id),
            payload=serialize_model(run),
            updated_at=datetime.now(UTC).isoformat(),
        )

    def get_run(self, run_id: UUID | str) -> RunRecord | None:
        payload = self._fetch_payload(
            self._control,
            table="runs",
            key_col="run_id",
            key_value=str(to_uuid(run_id)),
        )
        if payload is None:
            return None
        return RunRecord.model_validate(json.loads(payload))

    def list_runs(self) -> list[RunRecord]:
        payloads = self._fetch_payloads(
            self._control,
            f"SELECT payload FROM {self._control.table('runs')} ORDER BY updated_at DESC",  # nosec B608
        )
        return [RunRecord.model_validate(json.loads(payload)) for payload in payloads]

    def save_published_agent(self, agent: PublishedAgent) -> None:
        self._upsert_payload(
            self._control,
            table="published_agents",
            key_col="agent_id",
            key_value=agent.agent_id,
            payload=serialize_model(agent),
            updated_at=datetime.now(UTC).isoformat(),
        )

    def get_published_agent(self, agent_id: str) -> PublishedAgent | None:
        payload = self._fetch_payload(
            self._control,
            table="published_agents",
            key_col="agent_id",
            key_value=agent_id,
        )
        if payload is None:
            return None
        return PublishedAgent.model_validate(json.loads(payload))

    def list_published_agents(self) -> list[PublishedAgent]:
        payloads = self._fetch_payloads(
            self._control,
            (
                f"SELECT payload FROM {self._control.table('published_agents')} "  # nosec B608
                "ORDER BY updated_at DESC"
            ),
        )
        return [PublishedAgent.model_validate(json.loads(payload)) for payload in payloads]

    def delete_published_agent(self, agent_id: str) -> bool:
        cursor = self._control.execute(
            (
                f"DELETE FROM {self._control.table('published_agents')} "  # nosec B608
                f"WHERE agent_id = {self._control.placeholder}"
            ),
            (agent_id,),
            commit=True,
        )
        return bool(cursor.rowcount)

    def save_trajectory_step(self, step: TrajectoryStepRecord, position: int) -> None:
        placeholder = self._data.placeholder
        self._data.execute(  # nosec B608
            f"""
            INSERT INTO {self._data.table('trajectory')} (run_id, step_id, position, payload)
            VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder})
            ON CONFLICT(run_id, step_id) DO UPDATE SET
                position = excluded.position,
                payload = excluded.payload
            """,
            (str(step.run_id), step.id, position, serialize_model(step)),
            commit=True,
        )

    def append_trajectory_step(self, step: TrajectoryStepRecord) -> None:
        existing = self._data.fetchone(  # nosec B608
            f"""
            SELECT position
            FROM {self._data.table('trajectory')}
            WHERE run_id = {self._data.placeholder} AND step_id = {self._data.placeholder}
            """,
            (str(step.run_id), step.id),
        )
        if existing:
            position = int(existing["position"])
        else:
            row = self._data.fetchone(  # nosec B608
                f"""
                SELECT COALESCE(MAX(position), -1) + 1 AS next_position
                FROM {self._data.table('trajectory')}
                WHERE run_id = {self._data.placeholder}
                """,
                (str(step.run_id),),
            )
            position = int(row["next_position"]) if row else 0
        self.save_trajectory_step(step, position)

    def list_trajectory(self, run_id: UUID | str) -> list[TrajectoryStepRecord]:
        payloads = self._fetch_payloads(  # nosec B608
            self._data,
            f"""
            SELECT payload
            FROM {self._data.table('trajectory')}
            WHERE run_id = {self._data.placeholder}
            ORDER BY position ASC
            """,
            (str(to_uuid(run_id)),),
        )
        return [TrajectoryStepRecord.model_validate(json.loads(payload)) for payload in payloads]

    def persist_trajectory(self, run_id: UUID, steps: list[TrajectoryStepRecord]) -> None:
        self._data.execute(  # nosec B608
            f"DELETE FROM {self._data.table('trajectory')} WHERE run_id = {self._data.placeholder}",  # nosec B608
            (str(run_id),),
            commit=True,
        )
        for position, step in enumerate(steps):
            self.save_trajectory_step(step, position)

    def save_trace_span(self, span: TraceSpan, position: int) -> None:
        placeholder = self._data.placeholder
        self._data.execute(
            f"""
            INSERT INTO {self._data.table('trace_spans')} (run_id, span_id, position, payload)
            VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder})
            ON CONFLICT(run_id, span_id) DO UPDATE SET
                position = excluded.position,
                payload = excluded.payload
            """,
            (str(span.run_id), span.span_id, position, serialize_model(span)),
            commit=True,
        )

    def append_trace_span(self, span: TraceSpan) -> None:
        existing = self._data.fetchone(  # nosec B608
            f"""
            SELECT position
            FROM {self._data.table('trace_spans')}
            WHERE run_id = {self._data.placeholder} AND span_id = {self._data.placeholder}
            """,
            (str(span.run_id), span.span_id),
        )
        if existing:
            position = int(existing["position"])
        else:
            row = self._data.fetchone(  # nosec B608
                f"""
                SELECT COALESCE(MAX(position), -1) + 1 AS next_position
                FROM {self._data.table('trace_spans')}
                WHERE run_id = {self._data.placeholder}
                """,
                (str(span.run_id),),
            )
            position = int(row["next_position"]) if row else 0
        self.save_trace_span(span, position)

    def list_trace_spans(self, run_id: UUID | str) -> list[TraceSpan]:
        payloads = self._fetch_payloads(  # nosec B608
            self._data,
            f"""
            SELECT payload
            FROM {self._data.table('trace_spans')}
            WHERE run_id = {self._data.placeholder}
            ORDER BY position ASC
            """,
            (str(to_uuid(run_id)),),
        )
        return [TraceSpan.model_validate(json.loads(payload)) for payload in payloads]

    def persist_trace_spans(self, run_id: UUID, spans: list[TraceSpan]) -> None:
        self._data.execute(
            (
                f"DELETE FROM {self._data.table('trace_spans')} "  # nosec B608
                f"WHERE run_id = {self._data.placeholder}"
            ),
            (str(run_id),),
            commit=True,
        )
        for position, span in enumerate(spans):
            self.save_trace_span(span, position)

    def save_dataset(self, dataset: Dataset) -> None:
        timestamp = datetime.now(UTC).isoformat()
        self._upsert_payload(
            self._control,
            table="datasets",
            key_col="name",
            key_value=dataset.name,
            payload=serialize_model(dataset),
            updated_at=timestamp,
        )
        self._control.execute(  # nosec B608
            f"""
            DELETE FROM {self._control.table('dataset_versions')}
            WHERE dataset_name = {self._control.placeholder}
            """,
            (dataset.name,),
            commit=True,
        )
        placeholder = self._control.placeholder
        for version in dataset.versions:
            self._control.execute(  # nosec B608
                f"""
                INSERT INTO {self._control.table('dataset_versions')} (
                    dataset_version_id, dataset_name, payload, updated_at
                )
                VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder})
                ON CONFLICT(dataset_version_id) DO UPDATE SET
                    dataset_name = excluded.dataset_name,
                    payload = excluded.payload,
                    updated_at = excluded.updated_at
                """,
                (
                    str(version.dataset_version_id),
                    dataset.name,
                    serialize_model(version),
                    timestamp,
                ),
                commit=True,
            )

    def get_dataset(self, name: str) -> Dataset | None:
        payload = self._fetch_payload(
            self._control,
            table="datasets",
            key_col="name",
            key_value=name,
        )
        if payload is None:
            return None
        return Dataset.model_validate(json.loads(payload))

    def list_datasets(self) -> list[Dataset]:
        payloads = self._fetch_payloads(
            self._control,
            f"SELECT payload FROM {self._control.table('datasets')} ORDER BY updated_at DESC",  # nosec B608
        )
        return [Dataset.model_validate(json.loads(payload)) for payload in payloads]

    def get_dataset_version(self, dataset_version_id: UUID | str) -> DatasetVersion | None:
        rows = self._fetch_payloads(  # nosec B608
            self._control,
            f"""
            SELECT payload
            FROM {self._control.table('dataset_versions')}
            WHERE dataset_version_id = {self._control.placeholder}
            LIMIT 1
            """,
            (str(to_uuid(dataset_version_id)),),
        )
        if not rows:
            return None
        return DatasetVersion.model_validate(json.loads(rows[0]))

    def save_experiment(self, experiment: ExperimentRecord) -> None:
        self._upsert_payload(
            self._control,
            table="experiments",
            key_col="experiment_id",
            key_value=str(experiment.experiment_id),
            payload=json.dumps(
                experiment.model_dump(mode="json", by_alias=True),
                ensure_ascii=False,
            ),
            updated_at=datetime.now(UTC).isoformat(),
        )

    def get_experiment(self, experiment_id: UUID | str) -> ExperimentRecord | None:
        payload = self._fetch_payload(
            self._control,
            table="experiments",
            key_col="experiment_id",
            key_value=str(to_uuid(experiment_id)),
        )
        if payload is None:
            return None
        return ExperimentRecord.model_validate(_normalize_experiment_payload(json.loads(payload)))

    def list_experiments(self) -> list[ExperimentRecord]:
        payloads = self._fetch_payloads(
            self._control,
            f"SELECT payload FROM {self._control.table('experiments')} ORDER BY updated_at DESC",  # nosec B608
        )
        return [
            ExperimentRecord.model_validate(_normalize_experiment_payload(json.loads(payload)))
            for payload in payloads
        ]

    def save_run_evaluation(self, record: RunEvaluationRecord) -> None:
        placeholder = self._data.placeholder
        self._data.execute(  # nosec B608
            f"""
            INSERT INTO {self._data.table('run_evaluations')} (
                run_id, experiment_id, dataset_sample_id, payload, updated_at
            )
            VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder})
            ON CONFLICT(run_id) DO UPDATE SET
                experiment_id = excluded.experiment_id,
                dataset_sample_id = excluded.dataset_sample_id,
                payload = excluded.payload,
                updated_at = excluded.updated_at
            """,
            (
                str(record.run_id),
                str(record.experiment_id),
                record.dataset_sample_id,
                serialize_model(record),
                datetime.now(UTC).isoformat(),
            ),
            commit=True,
        )

    def list_run_evaluations(self, experiment_id: UUID | str) -> list[RunEvaluationRecord]:
        payloads = self._fetch_payloads(  # nosec B608
            self._data,
            f"""
            SELECT payload
            FROM {self._data.table('run_evaluations')}
            WHERE experiment_id = {self._data.placeholder}
            ORDER BY dataset_sample_id ASC
            """,
            (str(to_uuid(experiment_id)),),
        )
        return [RunEvaluationRecord.model_validate(json.loads(payload)) for payload in payloads]

    def get_run_evaluation_by_run(self, run_id: UUID | str) -> RunEvaluationRecord | None:
        payloads = self._fetch_payloads(  # nosec B608
            self._data,
            f"""
            SELECT payload
            FROM {self._data.table('run_evaluations')}
            WHERE run_id = {self._data.placeholder}
            LIMIT 1
            """,
            (str(to_uuid(run_id)),),
        )
        if not payloads:
            return None
        return RunEvaluationRecord.model_validate(json.loads(payloads[0]))

    def delete_run_evaluations(self, experiment_id: UUID | str) -> None:
        self._data.execute(  # nosec B608
            f"""
            DELETE FROM {self._data.table('run_evaluations')}
            WHERE experiment_id = {self._data.placeholder}
            """,
            (str(to_uuid(experiment_id)),),
            commit=True,
        )

    def save_approval_policy(self, policy: ApprovalPolicyRecord) -> None:
        timestamp = datetime.now(UTC).isoformat()
        self._upsert_payload(
            self._control,
            table="approval_policies",
            key_col="approval_policy_id",
            key_value=str(policy.approval_policy_id),
            payload=serialize_model(policy),
            updated_at=timestamp,
        )
        self._control.execute(  # nosec B608
            f"""
            DELETE FROM {self._control.table('tool_policies')}
            WHERE approval_policy_id = {self._control.placeholder}
            """,
            (str(policy.approval_policy_id),),
            commit=True,
        )
        placeholder = self._control.placeholder
        for rule in policy.tool_policies:
            self._control.execute(  # nosec B608
                f"""
                INSERT INTO {self._control.table('tool_policies')} (
                    approval_policy_id, tool_name, payload, updated_at
                )
                VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder})
                ON CONFLICT(approval_policy_id, tool_name) DO UPDATE SET
                    payload = excluded.payload,
                    updated_at = excluded.updated_at
                """,
                (
                    str(policy.approval_policy_id),
                    rule.tool_name,
                    serialize_model(rule),
                    timestamp,
                ),
                commit=True,
            )

    def get_approval_policy(self, approval_policy_id: UUID | str) -> ApprovalPolicyRecord | None:
        payload = self._fetch_payload(
            self._control,
            table="approval_policies",
            key_col="approval_policy_id",
            key_value=str(to_uuid(approval_policy_id)),
        )
        if payload is None:
            return None
        return ApprovalPolicyRecord.model_validate(json.loads(payload))

    def list_approval_policies(self) -> list[ApprovalPolicyRecord]:
        payloads = self._fetch_payloads(
            self._control,
            (
                f"SELECT payload FROM {self._control.table('approval_policies')} "  # nosec B608
                "ORDER BY updated_at DESC"
            ),
        )
        return [ApprovalPolicyRecord.model_validate(json.loads(payload)) for payload in payloads]

    def save_artifact(self, artifact: ArtifactMetadata) -> None:
        self._upsert_payload(
            self._data,
            table="artifacts",
            key_col="artifact_id",
            key_value=str(artifact.artifact_id),
            payload=serialize_model(artifact),
            updated_at=artifact.created_at.isoformat(),
        )

    def get_artifact(self, artifact_id: UUID | str) -> ArtifactMetadata | None:
        payload = self._fetch_payload(
            self._data,
            table="artifacts",
            key_col="artifact_id",
            key_value=str(to_uuid(artifact_id)),
        )
        if payload is None:
            return None
        return ArtifactMetadata.model_validate(json.loads(payload))

    def list_artifacts(self) -> list[ArtifactMetadata]:
        payloads = self._fetch_payloads(
            self._data,
            f"SELECT payload FROM {self._data.table('artifacts')} ORDER BY updated_at DESC",  # nosec B608
        )
        return [ArtifactMetadata.model_validate(json.loads(payload)) for payload in payloads]

    def enqueue_task(self, task: QueuedTask) -> None:
        placeholder = self._control.placeholder
        self._control.execute(  # nosec B608
            f"""
            INSERT INTO {self._control.table('tasks')} (
                task_id, task_type, target_id, payload, status, attempts, error,
                claimed_by, claimed_at, created_at, updated_at
            )
            VALUES (
                {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder},
                {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder},
                {placeholder}
            )
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
            commit=True,
        )

    def claim_next_task(self, worker_name: str, lease_seconds: int) -> QueuedTask | None:
        row = self._control.claim_next_task(worker_name, lease_seconds)
        if row is None:
            return None
        return self._task_from_row(row)

    def mark_task_done(self, task_id: UUID | str) -> None:
        self._update_task_status(task_id, TaskStatus.SUCCEEDED)

    def mark_task_failed(self, task_id: UUID | str, error: str) -> None:
        self._update_task_status(task_id, TaskStatus.FAILED, error=error)

    def reset(self) -> None:
        self.reset_all()

    def _update_task_status(
        self,
        task_id: UUID | str,
        status: TaskStatus,
        *,
        error: str | None = None,
    ) -> None:
        self._control.execute(  # nosec B608
            f"""
            UPDATE {self._control.table('tasks')}
            SET status = {self._control.placeholder},
                error = {self._control.placeholder},
                updated_at = {self._control.placeholder}
            WHERE task_id = {self._control.placeholder}
            """,
            (
                status.value,
                error,
                datetime.now(UTC).isoformat(),
                str(to_uuid(task_id)),
            ),
            commit=True,
        )

    @staticmethod
    def _task_from_row(row: dict[str, Any]) -> QueuedTask:
        return QueuedTask.model_validate(
            {
                "task_id": row["task_id"],
                "task_type": row["task_type"],
                "target_id": row["target_id"],
                "payload": json.loads(row["payload"]),
                "status": row["status"],
                "attempts": row["attempts"],
                "error": row["error"],
                "claimed_by": row["claimed_by"],
                "claimed_at": row["claimed_at"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
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
        experiments = {
            to_uuid(experiment.experiment_id): experiment for experiment in self.list_experiments()
        }
        artifacts = {to_uuid(artifact.artifact_id): artifact for artifact in self.list_artifacts()}
        return {
            "runs": runs,
            "trajectory": trajectory,
            "trace_spans": trace_spans,
            "datasets": datasets,
            "experiments": experiments,
            "artifacts": artifacts,
        }

    def reset_all(self) -> None:
        self._data.delete_all(
            [
                "trace_spans",
                "trajectory",
                "run_evaluations",
                "artifacts",
            ]
        )
        self._control.delete_all(
            [
                "dataset_versions",
                "datasets",
                "experiments",
                "tool_policies",
                "approval_policies",
                "published_agents",
                "runs",
                "tasks",
            ]
        )

    def close(self) -> None:
        self._data.close()
        self._control.close()


def build_state_persistence() -> StatePersistence:
    control_database_url = settings.control_plane_database_url or settings.database_url
    data_database_url = settings.data_plane_database_url or settings.database_url
    return StatePersistence(
        control_database_url=control_database_url,
        data_database_url=data_database_url,
        control_schema=settings.control_plane_database_schema,
        data_schema=settings.data_plane_database_schema,
    )
