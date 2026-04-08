from __future__ import annotations

import json
from datetime import UTC, datetime

from app.db.persistence import (
    PlaneStoreSet,
    fetch_payload,
    fetch_payloads,
    serialize_model,
    upsert_payload,
)
from app.infrastructure.repositories.common import PlaneStoreSetSource, resolve_state_store
from app.modules.agents.domain.models import GovernedPublishedAgent


class StatePublishedAgentRepository:
    def __init__(self, stores: PlaneStoreSetSource = None) -> None:
        self._store_source = stores
        self.init_schema()

    @property
    def _stores(self) -> PlaneStoreSet:
        return resolve_state_store(self._store_source)

    def init_schema(self) -> None:
        self._stores.control.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {self._stores.control.table('published_agents')} (
                agent_id TEXT PRIMARY KEY,
                payload TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """,
            commit=True,
        )

    def reset_state(self) -> None:
        self._stores.control.delete_all(["published_agents"])

    def list_agents(self) -> list[GovernedPublishedAgent]:
        payloads = fetch_payloads(
            self._stores.control,
            (
                f"SELECT payload FROM {self._stores.control.table('published_agents')} "  # nosec B608
                "ORDER BY updated_at DESC"
            ),
        )
        return [GovernedPublishedAgent.model_validate(json.loads(payload)) for payload in payloads]

    def get_agent(self, agent_id: str) -> GovernedPublishedAgent | None:
        payload = fetch_payload(
            self._stores.control,
            table="published_agents",
            key_col="agent_id",
            key_value=agent_id,
        )
        if payload is None:
            return None
        return GovernedPublishedAgent.model_validate(json.loads(payload))

    def save_agent(self, agent: GovernedPublishedAgent) -> None:
        upsert_payload(
            self._stores.control,
            table="published_agents",
            key_col="agent_id",
            key_value=agent.agent_id,
            payload=serialize_model(agent),
            updated_at=datetime.now(UTC).isoformat(),
        )

    def delete_agent(self, agent_id: str) -> bool:
        cursor = self._stores.control.execute(
            (
                f"DELETE FROM {self._stores.control.table('published_agents')} "  # nosec B608
                f"WHERE agent_id = {self._stores.control.placeholder}"
            ),
            (agent_id,),
            commit=True,
        )
        return bool(cursor.rowcount)


__all__ = ["StatePublishedAgentRepository"]
