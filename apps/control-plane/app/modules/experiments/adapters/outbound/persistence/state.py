from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import UUID

from app.db.persistence import (
    PlaneStoreSet,
    delete_by_column,
    fetch_payload,
    fetch_payloads,
    fetch_payloads_by_column,
    serialize_model,
    upsert_payload,
    upsert_record,
)
from app.infrastructure.repositories.common import (
    PlaneStoreSetSource,
    resolve_state_store,
    to_uuid,
)
from app.modules.experiments.domain.models import ExperimentRecord, RunEvaluationRecord


class _ExperimentsStoreBacked:
    def __init__(self, stores: PlaneStoreSetSource = None) -> None:
        self._store_source = stores
        self.init_schema()

    @property
    def _stores(self) -> PlaneStoreSet:
        return resolve_state_store(self._store_source)

    def init_schema(self) -> None:
        raise NotImplementedError


class StateExperimentRepository(_ExperimentsStoreBacked):
    def init_schema(self) -> None:
        self._stores.control.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {self._stores.control.table('experiments')} (
                experiment_id TEXT PRIMARY KEY,
                payload TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """,
            commit=True,
        )

    def reset_state(self) -> None:
        self._stores.control.delete_all(["experiments"])

    def list(self) -> list[ExperimentRecord]:
        payloads = fetch_payloads(
            self._stores.control,
            (
                f"SELECT payload FROM {self._stores.control.table('experiments')} "  # nosec B608
                "ORDER BY updated_at DESC"
            ),
        )
        return [ExperimentRecord.model_validate(json.loads(payload)) for payload in payloads]

    def get(self, experiment_id: str | UUID) -> ExperimentRecord | None:
        payload = fetch_payload(
            self._stores.control,
            table="experiments",
            key_col="experiment_id",
            key_value=str(to_uuid(experiment_id)),
        )
        if payload is None:
            return None
        return ExperimentRecord.model_validate(json.loads(payload))

    def save(self, experiment: ExperimentRecord) -> None:
        upsert_payload(
            self._stores.control,
            table="experiments",
            key_col="experiment_id",
            key_value=str(experiment.experiment_id),
            payload=serialize_model(experiment),
            updated_at=datetime.now(UTC).isoformat(),
        )


class StateRunEvaluationRepository(_ExperimentsStoreBacked):
    def init_schema(self) -> None:
        self._stores.data.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {self._stores.data.table('run_evaluations')} (
                run_id TEXT PRIMARY KEY,
                experiment_id TEXT NOT NULL,
                dataset_sample_id TEXT NOT NULL,
                payload TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """,
            commit=True,
        )

    def reset_state(self) -> None:
        self._stores.data.delete_all(["run_evaluations"])

    def list_for_experiment(self, experiment_id: str | UUID) -> list[RunEvaluationRecord]:
        payloads = fetch_payloads_by_column(
            self._stores.data,
            table="run_evaluations",
            key_col="experiment_id",
            key_value=str(to_uuid(experiment_id)),
            order_by="dataset_sample_id",
        )
        return [RunEvaluationRecord.model_validate(json.loads(payload)) for payload in payloads]

    def get_by_run(self, run_id: str | UUID) -> RunEvaluationRecord | None:
        payload = fetch_payload(
            self._stores.data,
            table="run_evaluations",
            key_col="run_id",
            key_value=str(to_uuid(run_id)),
        )
        if payload is None:
            return None
        return RunEvaluationRecord.model_validate(json.loads(payload))

    def save(self, record: RunEvaluationRecord) -> None:
        upsert_record(
            self._stores.data,
            table="run_evaluations",
            columns=("run_id", "experiment_id", "dataset_sample_id", "payload", "updated_at"),
            values=(
                str(record.run_id),
                str(record.experiment_id),
                record.dataset_sample_id,
                serialize_model(record),
                datetime.now(UTC).isoformat(),
            ),
            conflict_columns=("run_id",),
            update_columns=("experiment_id", "dataset_sample_id", "payload", "updated_at"),
        )

    def delete_for_experiment(self, experiment_id: str | UUID) -> None:
        delete_by_column(
            self._stores.data,
            table="run_evaluations",
            key_col="experiment_id",
            key_value=str(to_uuid(experiment_id)),
        )


__all__ = ["StateExperimentRepository", "StateRunEvaluationRepository"]
