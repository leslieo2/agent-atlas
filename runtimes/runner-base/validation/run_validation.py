from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from uuid import uuid4

BUNDLE_ARTIFACT_REF = "file:///opt/atlas-validation/project-bundle.tar.gz"
CANONICAL_MOUNT_PATH = "/workspace/project"
DEFAULT_IMAGE_TAG = "atlas-claude-validation:local"
PROMPT = (
    "Edit app.py so TARGET becomes \"after\". "
    "Do not change any other file. "
    "When finished, reply with one short confirmation sentence."
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="run_validation.py",
        description="Build the controlled Claude Code validation image and run one end-to-end check.",
    )
    parser.add_argument(
        "--repo-root",
        default=str(Path(__file__).resolve().parents[3]),
        help="Absolute path to the agent-atlas repository root.",
    )
    parser.add_argument(
        "--image-tag",
        default=DEFAULT_IMAGE_TAG,
        help="Docker image tag used for the controlled validation carrier.",
    )
    parser.add_argument(
        "--skip-build",
        action="store_true",
        help="Reuse an existing local image instead of rebuilding it.",
    )
    return parser.parse_args()


def _copy_auth_material(temp_home: Path) -> None:
    host_claude_dir = Path.home() / ".claude"
    host_claude_json = Path.home() / ".claude.json"
    if not host_claude_dir.exists() or not host_claude_json.exists():
        raise RuntimeError(
            "controlled validation requires host Claude auth at ~/.claude and ~/.claude.json"
        )

    shutil.copytree(host_claude_dir, temp_home / ".claude")
    shutil.copy2(host_claude_json, temp_home / ".claude.json")


def _runner_run_spec() -> dict[str, object]:
    run_id = str(uuid4())
    experiment_id = str(uuid4())
    attempt_id = str(uuid4())
    return {
        "schema_version": "runner-run-spec.v1",
        "run_id": run_id,
        "runner_backend": "k8s-container",
        "experiment_id": experiment_id,
        "attempt": 1,
        "attempt_id": attempt_id,
        "project": "atlas-validation",
        "dataset": "controlled-validation",
        "agent_id": "claude-code-validation",
        "model": "",
        "entrypoint": None,
        "agent_type": "external-runner",
        "prompt": PROMPT,
        "tags": ["validation", "claude-code", "project-in-container"],
        "project_metadata": {
            "prompt_version": "validation-v1",
            "validation_image": DEFAULT_IMAGE_TAG,
        },
        "executor_config": {
            "backend": "external-runner",
            "runner_image": DEFAULT_IMAGE_TAG,
            "metadata": {
                "runner_backend": "k8s-container",
                "project_materialization": {
                    "mode": "artifact_bundle",
                    "artifact_ref": BUNDLE_ARTIFACT_REF,
                    "mount_path": CANONICAL_MOUNT_PATH,
                },
                "claude_code_cli": {
                    "command": "claude",
                    "args": ["--dangerously-skip-permissions"],
                    "version": "validation",
                },
            },
        },
        "framework": "claude-code-cli",
        "artifact_ref": None,
        "image_ref": None,
        "trace_backend": "state",
        "tracing": None,
        "published_agent_snapshot": {
            "manifest": {
                "agent_id": "claude-code-validation",
                "name": "Claude Validation Carrier",
                "framework": "claude-code-cli",
            }
        },
        "bootstrap": {
            "run_spec_path": "/workspace/input/run_spec.json",
            "events_path": "/workspace/output/events.ndjson",
            "runtime_result_path": "/workspace/output/runtime_result.json",
            "terminal_result_path": "/workspace/output/terminal_result.json",
            "artifact_manifest_path": "/workspace/output/artifact_manifest.json",
            "artifact_dir": "/workspace/output/artifacts",
        },
    }


def _run(cmd: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        cmd,
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode == 0:
        return completed
    raise RuntimeError(
        f"command failed ({completed.returncode}): {' '.join(cmd)}\n"
        f"stdout:\n{completed.stdout}\n"
        f"stderr:\n{completed.stderr}"
    )


def main() -> int:
    args = _parse_args()
    repo_root = Path(args.repo_root).resolve()
    validation_root = repo_root / "runtimes" / "runner-base" / "validation"
    dockerfile = validation_root / "Dockerfile"

    with tempfile.TemporaryDirectory(prefix="atlas-claude-validation-") as temp_dir:
        temp_root = Path(temp_dir)
        temp_home = temp_root / "home"
        input_dir = temp_root / "input"
        output_dir = temp_root / "output"
        artifacts_dir = output_dir / "artifacts"
        temp_home.mkdir(parents=True, exist_ok=True)
        input_dir.mkdir(parents=True, exist_ok=True)
        artifacts_dir.mkdir(parents=True, exist_ok=True)

        _copy_auth_material(temp_home)

        if not args.skip_build:
            _run(
                [
                    "docker",
                    "build",
                    "-f",
                    str(dockerfile),
                    "-t",
                    args.image_tag,
                    ".",
                ],
                cwd=repo_root,
            )

        run_spec = _runner_run_spec()
        run_spec["project_metadata"]["validation_image"] = args.image_tag
        run_spec["executor_config"]["runner_image"] = args.image_tag
        run_spec_path = input_dir / "run_spec.json"
        run_spec_path.write_text(json.dumps(run_spec, indent=2), encoding="utf-8")

        runtime_cmd = [
            "docker",
            "run",
            "--rm",
            "-e",
            "HOME=/home/atlas",
            "-v",
            f"{temp_home}:/home/atlas",
            "-v",
            f"{input_dir}:/workspace/input",
            "-v",
            f"{output_dir}:/workspace/output",
            args.image_tag,
            "python",
            "-m",
            "agent_atlas_runner_base.claude_code",
            "--run-spec",
            "/workspace/input/run_spec.json",
            "--events",
            "/workspace/output/events.ndjson",
            "--runtime-result",
            "/workspace/output/runtime_result.json",
            "--terminal-result",
            "/workspace/output/terminal_result.json",
            "--artifact-manifest",
            "/workspace/output/artifact_manifest.json",
            "--artifact-dir",
            "/workspace/output/artifacts",
        ]
        _run(runtime_cmd, cwd=repo_root)

        terminal_result = json.loads((output_dir / "terminal_result.json").read_text())
        runtime_result = json.loads((output_dir / "runtime_result.json").read_text())
        artifact_manifest = json.loads((output_dir / "artifact_manifest.json").read_text())

        changed_files_entry = next(
            item for item in artifact_manifest["artifacts"] if item["path"] == "workspace/changed-files.json"
        )
        changed_files = json.loads((artifacts_dir / changed_files_entry["path"]).read_text())
        transcript_entry = next(
            item for item in artifact_manifest["artifacts"] if item["path"] == "transcripts/claude-stream.jsonl"
        )
        transcript_excerpt = (artifacts_dir / transcript_entry["path"]).read_text(
            encoding="utf-8"
        ).splitlines()[:6]

        summary = {
            "image_tag": args.image_tag,
            "artifact_ref": BUNDLE_ARTIFACT_REF,
            "mount_path": CANONICAL_MOUNT_PATH,
            "terminal_status": terminal_result["status"],
            "terminal_reason_code": terminal_result["reason_code"],
            "runtime_provider": runtime_result["provider"],
            "runtime_execution_backend": runtime_result["execution_backend"],
            "changed_files": changed_files,
            "transcript_excerpt": transcript_excerpt,
            "artifact_paths": [item["path"] for item in artifact_manifest["artifacts"]],
            "output_dir": str(output_dir),
        }
        print(json.dumps(summary, indent=2, ensure_ascii=False))

        if terminal_result["status"] != "succeeded":
            raise RuntimeError("controlled validation did not succeed")
        if "app.py" not in changed_files["modified"]:
            raise RuntimeError("controlled validation did not record app.py as modified")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
