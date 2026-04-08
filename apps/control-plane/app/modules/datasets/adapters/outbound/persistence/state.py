from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import UUID

from app.db.persistence import (
    PlaneStoreSet,
    delete_by_column,
    fetch_payload,
    fetch_payloads,
    serialize_model,
    upsert_payload,
    upsert_record,
)
from app.infrastructure.repositories.common import (
    PlaneStoreSetSource,
    resolve_state_store,
    to_uuid,
)
from app.modules.datasets.domain.models import Dataset, DatasetVersion


class StateDatasetRepository:
    def __init__(self, stores: PlaneStoreSetSource = None) -> None:
        self._store_source = stores
        self.init_schema()

    @property
    def _stores(self) -> PlaneStoreSet:
        return resolve_state_store(self._store_source)

    def init_schema(self) -> None:
        datasets = self._stores.control.table("datasets")
        dataset_versions = self._stores.control.table("dataset_versions")
        statements = [
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
        ]
        for statement in statements:
            self._stores.control.execute(statement, commit=True)

    def reset_state(self) -> None:
        self._stores.control.delete_all(["dataset_versions", "datasets"])

    def list(self) -> list[Dataset]:
        payloads = fetch_payloads(
            self._stores.control,
            (
                f"SELECT payload FROM {self._stores.control.table('datasets')} "  # nosec B608
                "ORDER BY updated_at DESC"
            ),
        )
        return [Dataset.model_validate(json.loads(payload)) for payload in payloads]

    def get(self, name: str) -> Dataset | None:
        payload = fetch_payload(
            self._stores.control,
            table="datasets",
            key_col="name",
            key_value=name,
        )
        if payload is None:
            return None
        return Dataset.model_validate(json.loads(payload))

    def get_version(self, dataset_version_id: UUID | str) -> DatasetVersion | None:
        payload = fetch_payload(
            self._stores.control,
            table="dataset_versions",
            key_col="dataset_version_id",
            key_value=str(to_uuid(dataset_version_id)),
        )
        if payload is None:
            return None
        return DatasetVersion.model_validate(json.loads(payload))

    def save(self, dataset: Dataset) -> None:
        timestamp = datetime.now(UTC).isoformat()
        upsert_payload(
            self._stores.control,
            table="datasets",
            key_col="name",
            key_value=dataset.name,
            payload=serialize_model(dataset),
            updated_at=timestamp,
        )
        delete_by_column(
            self._stores.control,
            table="dataset_versions",
            key_col="dataset_name",
            key_value=dataset.name,
        )
        for version in dataset.versions:
            upsert_record(
                self._stores.control,
                table="dataset_versions",
                columns=("dataset_version_id", "dataset_name", "payload", "updated_at"),
                values=(
                    str(version.dataset_version_id),
                    dataset.name,
                    serialize_model(version),
                    timestamp,
                ),
                conflict_columns=("dataset_version_id",),
                update_columns=("dataset_name", "payload", "updated_at"),
            )


__all__ = ["StateDatasetRepository"]
