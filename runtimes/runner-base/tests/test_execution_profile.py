from __future__ import annotations

from agent_atlas_runner_base.execution_profile import (
    artifact_path,
    execution_binding,
    execution_plane_config,
    execution_plane_value,
    runner_image,
)


def test_execution_profile_prefers_binding_values_and_normalizes_strings() -> None:
    executor_config = {
        "binding": {
            "runner_image": "  atlas-runner:latest  ",
            "artifact_path": "  /artifacts/bundle.tar.gz  ",
            "config": {
                "job_namespace": "atlas-jobs",
            },
        },
        "runner_image": "fallback-image",
        "artifact_path": "fallback-artifact",
        "metadata": {
            "job_namespace": "fallback-namespace",
            "service_account": "atlas-runner",
        },
    }

    assert execution_binding(executor_config) == executor_config["binding"]
    assert execution_plane_config(executor_config) == {"job_namespace": "atlas-jobs"}
    assert runner_image(executor_config) == "atlas-runner:latest"
    assert artifact_path(executor_config) == "/artifacts/bundle.tar.gz"
    assert execution_plane_value(executor_config, "job_namespace") == "atlas-jobs"
    assert execution_plane_value(executor_config, "service_account") is None


def test_execution_profile_falls_back_to_metadata_and_top_level_values() -> None:
    executor_config = {
        "runner_image": "atlas-runner:stable",
        "artifact_path": "bundle://atlas-run",
        "metadata": {
            "job_namespace": "atlas-jobs",
        },
    }

    assert execution_binding(executor_config) == {}
    assert execution_plane_config(executor_config) == {"job_namespace": "atlas-jobs"}
    assert runner_image(executor_config) == "atlas-runner:stable"
    assert artifact_path(executor_config) == "bundle://atlas-run"
    assert execution_plane_value(executor_config, "job_namespace") == "atlas-jobs"

