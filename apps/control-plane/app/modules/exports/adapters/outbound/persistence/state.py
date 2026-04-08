from __future__ import annotations

import json
from uuid import UUID

from app.db.persistence import (
    PlaneStoreSet,
    fetch_payload,
    fetch_payloads,
    serialize_model,
    upsert_payload,
)
from app.infrastructure.repositories.common import (
    PlaneStoreSetSource,
    resolve_state_store,
    to_uuid,
)
from app.modules.exports.domain.models import ArtifactMetadata


class StateExportRepository:
    def __init__(self, stores: PlaneStoreSetSource = None) -> None:
        self._store_source = stores
        self.init_schema()

    @property
    def _stores(self) -> PlaneStoreSet:
        return resolve_state_store(self._store_source)

    def init_schema(self) -> None:
        self._stores.data.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {self._stores.data.table('artifacts')} (
                artifact_id TEXT PRIMARY KEY,
                payload TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """,
            commit=True,
        )

    def reset_state(self) -> None:
        self._stores.data.delete_all(["artifacts"])

    def get(self, artifact_id: str | UUID) -> ArtifactMetadata | None:
        payload = fetch_payload(
            self._stores.data,
            table="artifacts",
            key_col="artifact_id",
            key_value=str(to_uuid(artifact_id)),
        )
        if payload is None:
            return None
        return ArtifactMetadata.model_validate(json.loads(payload))

    def list(self) -> list[ArtifactMetadata]:
        payloads = fetch_payloads(
            self._stores.data,
            f"SELECT payload FROM {self._stores.data.table('artifacts')} ORDER BY updated_at DESC",  # nosec B608
        )
        return [ArtifactMetadata.model_validate(json.loads(payload)) for payload in payloads]

    def save(self, artifact: ArtifactMetadata) -> None:
        upsert_payload(
            self._stores.data,
            table="artifacts",
            key_col="artifact_id",
            key_value=str(artifact.artifact_id),
            payload=serialize_model(artifact),
            updated_at=artifact.created_at.isoformat(),
        )


__all__ = ["StateExportRepository"]
