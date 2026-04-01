from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def executor_metadata(executor_config: object) -> Mapping[str, Any]:
    if isinstance(executor_config, Mapping):
        metadata = executor_config.get("metadata")
    else:
        metadata = getattr(executor_config, "metadata", None)
    return metadata if isinstance(metadata, Mapping) else {}


def runner_image(executor_config: object) -> str | None:
    if isinstance(executor_config, Mapping):
        raw_value = executor_config.get("runner_image")
    else:
        raw_value = getattr(executor_config, "runner_image", None)
    if not isinstance(raw_value, str):
        return None
    normalized = raw_value.strip()
    return normalized or None


def requested_runner_backend(executor_config: object) -> str | None:
    metadata = executor_metadata(executor_config)
    raw_value = metadata.get("runner_backend")
    if not isinstance(raw_value, str):
        return None
    normalized = raw_value.strip().lower()
    return normalized or None


def uses_k8s_runner_backend(executor_config: object) -> bool:
    return requested_runner_backend(executor_config) == "k8s-container" or (
        runner_image(executor_config) is not None
    )
