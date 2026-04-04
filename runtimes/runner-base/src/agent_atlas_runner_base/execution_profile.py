from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def execution_binding(executor_config: Mapping[str, Any]) -> Mapping[str, Any]:
    binding = executor_config.get("binding")
    return binding if isinstance(binding, Mapping) else {}


def execution_plane_config(executor_config: Mapping[str, Any]) -> Mapping[str, Any]:
    binding = execution_binding(executor_config)
    config = binding.get("config")
    if isinstance(config, Mapping):
        return config
    metadata = executor_config.get("metadata")
    return metadata if isinstance(metadata, Mapping) else {}


def runner_image(executor_config: Mapping[str, Any]) -> str | None:
    binding = execution_binding(executor_config)
    raw_value = binding.get("runner_image")
    if not isinstance(raw_value, str):
        raw_value = executor_config.get("runner_image")
    if not isinstance(raw_value, str):
        return None
    normalized = raw_value.strip()
    return normalized or None


def artifact_path(executor_config: Mapping[str, Any]) -> str | None:
    binding = execution_binding(executor_config)
    raw_value = binding.get("artifact_path")
    if not isinstance(raw_value, str):
        raw_value = executor_config.get("artifact_path")
    if not isinstance(raw_value, str):
        return None
    normalized = raw_value.strip()
    return normalized or None


def execution_plane_value(executor_config: Mapping[str, Any], key: str) -> object | None:
    config = execution_plane_config(executor_config)
    if key in config:
        return config.get(key)
    return executor_config.get(key)
