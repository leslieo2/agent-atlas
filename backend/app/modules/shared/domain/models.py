from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel


def build_source_artifact_ref(agent_id: str, source_fingerprint: str) -> str:
    return f"source://{agent_id}@{source_fingerprint}"


class ProvenanceMetadata(BaseModel):
    framework: str | None = None
    published_agent_snapshot: dict[str, Any] | None = None
    artifact_ref: str | None = None
    image_ref: str | None = None
    runner_backend: str | None = None
    trace_backend: str | None = None
    eval_job_id: UUID | None = None
    dataset_sample_id: str | None = None
