from __future__ import annotations

import hashlib
import shutil
import tarfile
import zipfile
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agent_atlas_runner_base.constants import CANONICAL_MOUNT_PATH, WORKSPACE_PROJECT_MOUNT_PATH
from agent_atlas_runner_base.execution_profile import execution_plane_config


def _string_value(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


@dataclass(frozen=True)
class ProjectMaterializationConfig:
    mode: str
    artifact_ref: str
    readonly: bool = False


def project_materialization_from_executor_config(
    executor_config: Mapping[str, Any],
) -> ProjectMaterializationConfig | None:
    raw_config = execution_plane_config(executor_config).get("project_materialization")
    if not isinstance(raw_config, Mapping):
        return None

    mode = _string_value(raw_config.get("mode"))
    artifact_ref = _string_value(raw_config.get("artifact_ref"))
    mount_path = _string_value(raw_config.get("mount_path"))
    if mode is None or artifact_ref is None:
        return None
    if mode != "artifact_bundle":
        raise ValueError(f"unsupported project materialization mode: {mode}")
    if mount_path is not None and mount_path != CANONICAL_MOUNT_PATH:
        raise ValueError(
            f"artifact_bundle materialization only supports mount_path={CANONICAL_MOUNT_PATH}"
        )

    readonly = bool(raw_config.get("readonly", False))
    return ProjectMaterializationConfig(
        mode=mode,
        artifact_ref=artifact_ref,
        readonly=readonly,
    )


def materialize_project_bundle(config: ProjectMaterializationConfig) -> Path:
    source = _artifact_bundle_source_path(config.artifact_ref)
    if not source.exists():
        raise FileNotFoundError(f"artifact bundle not found: {config.artifact_ref}")

    target = WORKSPACE_PROJECT_MOUNT_PATH
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True, exist_ok=True)

    if source.is_dir():
        _copy_directory_contents(source, target)
    elif tarfile.is_tarfile(source):
        _extract_tar_bundle(source, target)
    elif zipfile.is_zipfile(source):
        _extract_zip_bundle(source, target)
    else:
        raise ValueError("artifact bundle must be a directory, tar archive, or zip archive")

    _flatten_single_root_directory(target)
    return target


def snapshot_tree(root: Path) -> dict[str, str]:
    if not root.exists():
        return {}
    snapshot: dict[str, str] = {}
    for candidate in sorted(path for path in root.rglob("*") if path.is_file()):
        relative_path = candidate.relative_to(root).as_posix()
        snapshot[relative_path] = hashlib.sha256(candidate.read_bytes()).hexdigest()
    return snapshot


def changed_files_manifest(
    *,
    before: Mapping[str, str],
    after: Mapping[str, str],
) -> dict[str, Any]:
    before_keys = set(before)
    after_keys = set(after)
    added = sorted(after_keys - before_keys)
    deleted = sorted(before_keys - after_keys)
    modified = sorted(path for path in before_keys & after_keys if before[path] != after[path])
    return {
        "added": added,
        "deleted": deleted,
        "modified": modified,
        "changed": sorted({*added, *deleted, *modified}),
    }


def _artifact_bundle_source_path(artifact_ref: str) -> Path:
    if not artifact_ref.startswith("file://"):
        raise ValueError("artifact_bundle materialization currently requires file:// artifact_ref")
    return Path(artifact_ref.removeprefix("file://"))


def _copy_directory_contents(source: Path, target: Path) -> None:
    for child in source.iterdir():
        destination = target / child.name
        if child.is_dir():
            shutil.copytree(child, destination)
        else:
            shutil.copy2(child, destination)


def _extract_tar_bundle(source: Path, target: Path) -> None:
    with tarfile.open(source) as archive:
        members = archive.getmembers()
        for member in members:
            member_path = (target / member.name).resolve()
            if not member_path.is_relative_to(target.resolve()):
                raise ValueError("artifact bundle contains unsafe tar path")
        archive.extractall(target, filter="data")


def _extract_zip_bundle(source: Path, target: Path) -> None:
    with zipfile.ZipFile(source) as archive:
        for member_name in archive.namelist():
            member_path = (target / member_name).resolve()
            if not member_path.is_relative_to(target.resolve()):
                raise ValueError("artifact bundle contains unsafe zip path")
        archive.extractall(target)


def _flatten_single_root_directory(target: Path) -> None:
    children = list(target.iterdir())
    if len(children) != 1 or not children[0].is_dir():
        return

    nested_root = children[0]
    temp_dir = target.parent / f"{target.name}.tmp-flatten"
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    temp_dir.mkdir(parents=True, exist_ok=True)

    for child in nested_root.iterdir():
        shutil.move(str(child), temp_dir / child.name)
    shutil.rmtree(target)
    temp_dir.rename(target)
