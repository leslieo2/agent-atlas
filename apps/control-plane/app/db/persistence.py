from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from threading import RLock
from typing import Any, Literal
from uuid import UUID

from app.core.config import settings

_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def to_uuid(value: UUID | str) -> UUID:
    if isinstance(value, UUID):
        return value
    return UUID(value)


def serialize_model(model: Any) -> str:
    return json.dumps(model.model_dump(mode="json"), ensure_ascii=False)


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


class PlaneStore:
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
            except ImportError as exc:  # pragma: no cover
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

    @staticmethod
    def _row_to_dict(row: Any) -> dict[str, Any] | None:
        if row is None:
            return None
        if isinstance(row, dict):
            return dict(row)
        return dict(row)


class PlaneStoreSet:
    def __init__(
        self,
        control_database_url: str | None = None,
        data_database_url: str | None = None,
        *,
        control_schema: str = "control_plane",
        data_schema: str = "data_plane",
    ) -> None:
        base_dir = Path(__file__).resolve().parents[2] / "data"
        self.control = PlaneStore(
            _PlaneConfig(
                name="control",
                database_url=control_database_url,
                default_sqlite_path=(base_dir / "control-plane-state.db").resolve(),
                postgres_schema=control_schema,
                sqlite_prefix="control_",
            )
        )
        self.data = PlaneStore(
            _PlaneConfig(
                name="data",
                database_url=data_database_url,
                default_sqlite_path=(base_dir / "data-plane-state.db").resolve(),
                postgres_schema=data_schema,
                sqlite_prefix="data_",
            )
        )
        self.enabled = self.control.enabled and self.data.enabled
        self.control.create_schema()
        self.data.create_schema()

    def close(self) -> None:
        self.data.close()
        self.control.close()


def upsert_payload(
    store: PlaneStore,
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


def fetch_payload(
    store: PlaneStore,
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


def fetch_payloads(
    store: PlaneStore,
    query: str,
    params: tuple[object, ...] = (),
) -> list[str]:
    rows = store.fetchall(query, params)
    return [str(row["payload"]) for row in rows]


def fetch_payloads_by_column(
    store: PlaneStore,
    *,
    table: str,
    key_col: str,
    key_value: object,
    order_by: str,
    descending: bool = False,
) -> list[str]:
    validated_key_col = _validate_identifier(key_col)
    validated_order_by = _validate_identifier(order_by)
    direction = "DESC" if descending else "ASC"
    rows = store.fetchall(  # nosec B608
        f"""
        SELECT payload
        FROM {store.table(table)}
        WHERE {validated_key_col} = {store.placeholder}
        ORDER BY {validated_order_by} {direction}
        """,
        (key_value,),
    )
    return [str(row["payload"]) for row in rows]


def fetch_row_by_columns(
    store: PlaneStore,
    *,
    table: str,
    select_cols: tuple[str, ...],
    where_cols: tuple[str, ...],
    where_values: tuple[object, ...],
) -> dict[str, Any] | None:
    validated_select_cols = ", ".join(_validate_identifier(col) for col in select_cols)
    validated_where_cols = tuple(_validate_identifier(col) for col in where_cols)
    predicates = " AND ".join(f"{col} = {store.placeholder}" for col in validated_where_cols)
    return store.fetchone(  # nosec B608
        f"""
        SELECT {validated_select_cols}
        FROM {store.table(table)}
        WHERE {predicates}
        LIMIT 1
        """,
        where_values,
    )


def fetch_next_position(
    store: PlaneStore,
    *,
    table: str,
    scope_col: str,
    scope_value: object,
    position_col: str = "position",
) -> int:
    validated_scope_col = _validate_identifier(scope_col)
    validated_position_col = _validate_identifier(position_col)
    row = store.fetchone(  # nosec B608
        f"""
        SELECT COALESCE(MAX({validated_position_col}), -1) + 1 AS next_position
        FROM {store.table(table)}
        WHERE {validated_scope_col} = {store.placeholder}
        """,
        (scope_value,),
    )
    return int(row["next_position"]) if row else 0


def delete_by_column(
    store: PlaneStore,
    *,
    table: str,
    key_col: str,
    key_value: object,
) -> None:
    validated_key_col = _validate_identifier(key_col)
    store.execute(  # nosec B608
        f"""
        DELETE FROM {store.table(table)}
        WHERE {validated_key_col} = {store.placeholder}
        """,
        (key_value,),
        commit=True,
    )


def upsert_record(
    store: PlaneStore,
    *,
    table: str,
    columns: tuple[str, ...],
    values: tuple[object, ...],
    conflict_columns: tuple[str, ...],
    update_columns: tuple[str, ...],
) -> None:
    validated_columns = tuple(_validate_identifier(col) for col in columns)
    validated_conflict_columns = tuple(_validate_identifier(col) for col in conflict_columns)
    validated_update_columns = tuple(_validate_identifier(col) for col in update_columns)
    column_list = ", ".join(validated_columns)
    placeholders = ", ".join(store.placeholder for _ in validated_columns)
    conflict_list = ", ".join(validated_conflict_columns)
    updates = ",\n            ".join(
        f"{column} = excluded.{column}" for column in validated_update_columns
    )
    store.execute(  # nosec B608
        f"""
        INSERT INTO {store.table(table)} ({column_list})
        VALUES ({placeholders})
        ON CONFLICT({conflict_list}) DO UPDATE SET
            {updates}
        """,
        values,
        commit=True,
    )


def build_plane_store_set() -> PlaneStoreSet:
    return PlaneStoreSet(
        control_database_url=settings.control_plane_database_url,
        data_database_url=settings.data_plane_database_url,
        control_schema=settings.control_plane_database_schema,
        data_schema=settings.data_plane_database_schema,
    )


__all__ = [
    "PlaneStore",
    "PlaneStoreSet",
    "build_plane_store_set",
    "delete_by_column",
    "fetch_next_position",
    "fetch_payload",
    "fetch_payloads",
    "fetch_payloads_by_column",
    "fetch_row_by_columns",
    "serialize_model",
    "to_uuid",
    "upsert_payload",
    "upsert_record",
]
