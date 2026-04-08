from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import UUID

from app.db.persistence import (
    PlaneStoreSet,
    fetch_next_position,
    fetch_payload,
    fetch_payloads,
    fetch_payloads_by_column,
    fetch_row_by_columns,
    serialize_model,
    upsert_payload,
    upsert_record,
)
from app.infrastructure.repositories.common import (
    PlaneStoreSetSource,
    resolve_state_store,
    to_uuid,
)
from app.modules.runs.domain.models import RunRecord
from app.modules.shared.domain.observability import TrajectoryStepRecord
from app.modules.shared.domain.traces import TraceSpan


class _RunsStoreBacked:
    def __init__(self, stores: PlaneStoreSetSource = None) -> None:
        self._store_source = stores
        self.init_schema()

    @property
    def _stores(self) -> PlaneStoreSet:
        return resolve_state_store(self._store_source)

    def init_schema(self) -> None:
        raise NotImplementedError


class StateRunRepository(_RunsStoreBacked):
    def init_schema(self) -> None:
        self._stores.control.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {self._stores.control.table('runs')} (
                run_id TEXT PRIMARY KEY,
                payload TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """,
            commit=True,
        )

    def reset_state(self) -> None:
        self._stores.control.delete_all(["runs"])

    def get(self, run_id: str | UUID) -> RunRecord | None:
        payload = fetch_payload(
            self._stores.control,
            table="runs",
            key_col="run_id",
            key_value=str(to_uuid(run_id)),
        )
        if payload is None:
            return None
        return RunRecord.model_validate(json.loads(payload))

    def list(self) -> list[RunRecord]:
        payloads = fetch_payloads(
            self._stores.control,
            f"SELECT payload FROM {self._stores.control.table('runs')} ORDER BY updated_at DESC",  # nosec B608
        )
        return [RunRecord.model_validate(json.loads(payload)) for payload in payloads]

    def save(self, run: RunRecord) -> None:
        upsert_payload(
            self._stores.control,
            table="runs",
            key_col="run_id",
            key_value=str(run.run_id),
            payload=serialize_model(run),
            updated_at=datetime.now(UTC).isoformat(),
        )


class StateTrajectoryRepository(_RunsStoreBacked):
    def init_schema(self) -> None:
        placeholder = self._stores.data.placeholder
        self._stores.data.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {self._stores.data.table('trajectory')} (
                run_id TEXT NOT NULL,
                step_id TEXT NOT NULL,
                position INTEGER NOT NULL,
                payload TEXT NOT NULL,
                PRIMARY KEY (run_id, step_id)
            )
            """,
            commit=True,
        )
        del placeholder

    def reset_state(self) -> None:
        self._stores.data.delete_all(["trajectory"])

    def list_for_run(self, run_id: str | UUID) -> list[TrajectoryStepRecord]:
        payloads = fetch_payloads_by_column(
            self._stores.data,
            table="trajectory",
            key_col="run_id",
            key_value=str(to_uuid(run_id)),
            order_by="position",
        )
        return [TrajectoryStepRecord.model_validate(json.loads(payload)) for payload in payloads]

    def append(self, step: TrajectoryStepRecord) -> None:
        existing = fetch_row_by_columns(
            self._stores.data,
            table="trajectory",
            select_cols=("position",),
            where_cols=("run_id", "step_id"),
            where_values=(str(step.run_id), step.id),
        )
        if existing:
            position = int(existing["position"])
        else:
            position = fetch_next_position(
                self._stores.data,
                table="trajectory",
                scope_col="run_id",
                scope_value=str(step.run_id),
            )
        upsert_record(
            self._stores.data,
            table="trajectory",
            columns=("run_id", "step_id", "position", "payload"),
            values=(str(step.run_id), step.id, position, serialize_model(step)),
            conflict_columns=("run_id", "step_id"),
            update_columns=("position", "payload"),
        )


class StateTraceRepository(_RunsStoreBacked):
    def init_schema(self) -> None:
        self._stores.data.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {self._stores.data.table('trace_spans')} (
                run_id TEXT NOT NULL,
                span_id TEXT NOT NULL,
                position INTEGER NOT NULL,
                payload TEXT NOT NULL,
                PRIMARY KEY (run_id, span_id)
            )
            """,
            commit=True,
        )

    def reset_state(self) -> None:
        self._stores.data.delete_all(["trace_spans"])

    def list_for_run(self, run_id: str | UUID) -> list[TraceSpan]:
        payloads = fetch_payloads_by_column(
            self._stores.data,
            table="trace_spans",
            key_col="run_id",
            key_value=str(to_uuid(run_id)),
            order_by="position",
        )
        return [TraceSpan.model_validate(json.loads(payload)) for payload in payloads]

    def append(self, span: TraceSpan) -> None:
        existing = fetch_row_by_columns(
            self._stores.data,
            table="trace_spans",
            select_cols=("position",),
            where_cols=("run_id", "span_id"),
            where_values=(str(span.run_id), span.span_id),
        )
        if existing:
            position = int(existing["position"])
        else:
            position = fetch_next_position(
                self._stores.data,
                table="trace_spans",
                scope_col="run_id",
                scope_value=str(span.run_id),
            )
        upsert_record(
            self._stores.data,
            table="trace_spans",
            columns=("run_id", "span_id", "position", "payload"),
            values=(str(span.run_id), span.span_id, position, serialize_model(span)),
            conflict_columns=("run_id", "span_id"),
            update_columns=("position", "payload"),
        )


__all__ = [
    "StateRunRepository",
    "StateTraceRepository",
    "StateTrajectoryRepository",
]
