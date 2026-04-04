from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def execution_binding(executor_config: object) -> Mapping[str, Any]:
    if isinstance(executor_config, Mapping):
        binding = executor_config.get("execution_binding") or executor_config.get("binding")
    else:
        binding = getattr(executor_config, "execution_binding", None)
    if isinstance(binding, Mapping):
        return binding
    model_dump = getattr(binding, "model_dump", None)
    if callable(model_dump):
        dumped = model_dump(mode="python", exclude_none=True)
        return dumped if isinstance(dumped, Mapping) else {}
    return {}


def execution_plane_config(executor_config: object) -> Mapping[str, Any]:
    binding = execution_binding(executor_config)
    config = binding.get("config")
    if isinstance(config, Mapping):
        return config

    if isinstance(executor_config, Mapping):
        metadata = executor_config.get("metadata")
    else:
        metadata = getattr(executor_config, "metadata", None)
    return metadata if isinstance(metadata, Mapping) else {}


def executor_metadata(executor_config: object) -> Mapping[str, Any]:
    return execution_plane_config(executor_config)


def runner_image(executor_config: object) -> str | None:
    binding = execution_binding(executor_config)
    raw_value = binding.get("runner_image")
    if not isinstance(raw_value, str):
        if isinstance(executor_config, Mapping):
            raw_value = executor_config.get("runner_image")
        else:
            raw_value = getattr(executor_config, "runner_image", None)
    if not isinstance(raw_value, str):
        return None
    normalized = raw_value.strip()
    return normalized or None


def artifact_path(executor_config: object) -> str | None:
    binding = execution_binding(executor_config)
    raw_value = binding.get("artifact_path")
    if not isinstance(raw_value, str):
        if isinstance(executor_config, Mapping):
            raw_value = executor_config.get("artifact_path")
        else:
            raw_value = getattr(executor_config, "artifact_path", None)
    if not isinstance(raw_value, str):
        return None
    normalized = raw_value.strip()
    return normalized or None


def execution_plane_value(executor_config: object, key: str) -> object | None:
    config = execution_plane_config(executor_config)
    if key in config:
        return config.get(key)
    if isinstance(executor_config, Mapping):
        return executor_config.get(key)
    else:
        return getattr(executor_config, key, None)


def requested_runner_backend(executor_config: object) -> str | None:
    binding = execution_binding(executor_config)
    raw_value = binding.get("runner_backend")
    if not isinstance(raw_value, str):
        metadata = executor_metadata(executor_config)
        raw_value = metadata.get("runner_backend")
    if not isinstance(raw_value, str):
        return None
    normalized = raw_value.strip().lower()
    return normalized or None


def uses_k8s_runner_backend(executor_config: object) -> bool:
    configured_runner_backend = requested_runner_backend(executor_config)
    if configured_runner_backend is not None:
        return configured_runner_backend == "k8s-container"
    return runner_image(executor_config) is not None
