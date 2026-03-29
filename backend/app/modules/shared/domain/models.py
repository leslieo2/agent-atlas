from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel


def build_source_artifact_ref(agent_id: str, source_fingerprint: str) -> str:
    return f"source://{agent_id}@{source_fingerprint}"


class RuntimeArtifactMetadata(BaseModel):
    build_status: str | None = None
    source_fingerprint: str | None = None
    framework: str | None = None
    entrypoint: str | None = None
    artifact_ref: str | None = None
    image_ref: str | None = None


def build_source_runtime_artifact(
    *,
    agent_id: str,
    source_fingerprint: str,
    framework: str,
    entrypoint: str,
) -> RuntimeArtifactMetadata:
    return RuntimeArtifactMetadata(
        build_status="ready",
        source_fingerprint=source_fingerprint,
        framework=framework,
        entrypoint=entrypoint,
        artifact_ref=build_source_artifact_ref(agent_id, source_fingerprint),
        image_ref=None,
    )


class ProvenanceMetadata(BaseModel):
    framework: str | None = None
    published_agent_snapshot: dict[str, Any] | None = None
    artifact_ref: str | None = None
    image_ref: str | None = None
    runner_backend: str | None = None
    trace_backend: str | None = None
    eval_job_id: UUID | None = None
    dataset_sample_id: str | None = None


class RuntimeArtifactBuildResult(BaseModel):
    runtime_artifact: RuntimeArtifactMetadata
    provenance: ProvenanceMetadata
