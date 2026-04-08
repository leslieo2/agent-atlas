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
from app.modules.policies.domain.models import ApprovalPolicyRecord


class StateApprovalPolicyRepository:
    def __init__(self, stores: PlaneStoreSetSource = None) -> None:
        self._store_source = stores
        self.init_schema()

    @property
    def _stores(self) -> PlaneStoreSet:
        return resolve_state_store(self._store_source)

    def init_schema(self) -> None:
        approval_policies = self._stores.control.table("approval_policies")
        tool_policies = self._stores.control.table("tool_policies")
        statements = [
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
        ]
        for statement in statements:
            self._stores.control.execute(statement, commit=True)

    def reset_state(self) -> None:
        self._stores.control.delete_all(["tool_policies", "approval_policies"])

    def list(self) -> list[ApprovalPolicyRecord]:
        payloads = fetch_payloads(
            self._stores.control,
            (
                f"SELECT payload FROM {self._stores.control.table('approval_policies')} "  # nosec B608
                "ORDER BY updated_at DESC"
            ),
        )
        return [ApprovalPolicyRecord.model_validate(json.loads(payload)) for payload in payloads]

    def get(self, approval_policy_id: str | UUID) -> ApprovalPolicyRecord | None:
        payload = fetch_payload(
            self._stores.control,
            table="approval_policies",
            key_col="approval_policy_id",
            key_value=str(to_uuid(approval_policy_id)),
        )
        if payload is None:
            return None
        return ApprovalPolicyRecord.model_validate(json.loads(payload))

    def save(self, policy: ApprovalPolicyRecord) -> None:
        timestamp = datetime.now(UTC).isoformat()
        upsert_payload(
            self._stores.control,
            table="approval_policies",
            key_col="approval_policy_id",
            key_value=str(policy.approval_policy_id),
            payload=serialize_model(policy),
            updated_at=timestamp,
        )
        delete_by_column(
            self._stores.control,
            table="tool_policies",
            key_col="approval_policy_id",
            key_value=str(policy.approval_policy_id),
        )
        for rule in policy.tool_policies:
            upsert_record(
                self._stores.control,
                table="tool_policies",
                columns=("approval_policy_id", "tool_name", "payload", "updated_at"),
                values=(
                    str(policy.approval_policy_id),
                    rule.tool_name,
                    serialize_model(rule),
                    timestamp,
                ),
                conflict_columns=("approval_policy_id", "tool_name"),
                update_columns=("payload", "updated_at"),
            )


__all__ = ["StateApprovalPolicyRepository"]
