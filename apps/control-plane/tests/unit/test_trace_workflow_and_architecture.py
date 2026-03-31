from __future__ import annotations

import ast
from pathlib import Path
from uuid import uuid4

from app.agent_tracing.adapters.trace_projector import TraceIngestProjector
from app.modules.shared.domain.enums import StepType
from app.modules.shared.domain.traces import TraceIngestEvent

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def test_trace_projector_normalizes_trace_event():
    projector = TraceIngestProjector()
    run_id = uuid4()
    event = TraceIngestEvent(
        run_id=run_id,
        span_id="span-123",
        parent_span_id=None,
        step_type=StepType.TOOL,
        name="ingest",
        input={"foo": "bar"},
        output={"ok": True},
        tool_name="mcp",
        latency_ms=7,
        token_usage=3,
        image_digest="sha256:test",
        prompt_version="v1",
    )

    normalized = projector.normalize(projector.project(event), event)
    assert normalized["run_id"] == str(run_id)
    assert normalized["step_type"] == "tool"


def test_api_does_not_import_infrastructure_modules():
    violations = _collect_forbidden_imports(
        base_dir=Path("app/api"),
        forbidden_prefixes=("app.infrastructure",),
    )
    assert violations == []


def test_module_domains_do_not_import_framework_or_storage_modules():
    violations = _collect_forbidden_imports(
        base_dir=Path("app/modules"),
        forbidden_prefixes=("fastapi", "sqlite3", "app.infrastructure", "app.db"),
        required_layer="domain",
    )
    assert violations == []


def test_module_applications_do_not_import_db_store():
    violations = _collect_forbidden_imports(
        base_dir=Path("app/modules"),
        forbidden_prefixes=("app.db",),
        required_layer="application",
    )
    assert violations == []


def test_shared_application_contracts_do_not_depend_on_agent_tracing() -> None:
    violations = _collect_forbidden_imports(
        base_dir=Path("app/modules/shared/application"),
        forbidden_prefixes=("app.agent_tracing",),
    )
    assert violations == []


def test_non_run_feature_modules_do_not_import_run_application_ports():
    violations = _collect_forbidden_imports(
        base_dir=Path("app/modules"),
        forbidden_prefixes=("app.modules.runs.application.ports",),
        allowed_paths=(Path("app/modules/runs"),),
    )
    assert violations == []


def test_runs_module_does_not_import_agent_tracing_ports() -> None:
    violations = _collect_forbidden_imports(
        base_dir=Path("app/modules/runs"),
        forbidden_prefixes=("app.agent_tracing.ports",),
    )
    assert violations == []


def test_agent_tracing_and_data_plane_do_not_import_run_module_ports() -> None:
    violations = _collect_forbidden_imports(
        base_dir=Path("app"),
        forbidden_prefixes=("app.modules.runs.application.ports",),
        allowed_paths=(
            Path("app/modules/runs"),
            Path("app/execution"),
            Path("app/bootstrap/wiring"),
        ),
    )
    assert violations == []


def test_agent_tracing_backends_do_not_import_run_domain_models() -> None:
    violations = _collect_forbidden_imports(
        base_dir=Path("app/agent_tracing/backends"),
        forbidden_prefixes=("app.modules.runs.domain.models",),
    )
    assert violations == []


def test_agent_tracing_and_data_plane_do_not_import_run_domain_models() -> None:
    tracing_violations = _collect_forbidden_imports(
        base_dir=Path("app/agent_tracing"),
        forbidden_prefixes=("app.modules.runs.domain.models",),
    )
    data_plane_violations = _collect_forbidden_imports(
        base_dir=Path("app/data_plane"),
        forbidden_prefixes=("app.modules.runs.domain.models",),
    )
    assert tracing_violations + data_plane_violations == []


def test_app_does_not_import_legacy_execution_plane_package():
    violations = _collect_forbidden_imports(
        base_dir=Path("app"),
        forbidden_prefixes=("app.execution_plane",),
    )
    assert violations == []


def test_feature_modules_do_not_import_other_feature_use_cases_or_execution():
    violations = _collect_cross_feature_application_imports(base_dir=Path("app/modules"))
    assert violations == []


def test_execution_plane_does_not_import_run_telemetry_module():
    violations = _collect_forbidden_imports(
        base_dir=Path("app/execution"),
        forbidden_prefixes=(
            "app.tracing",
            "app.modules.runs.application.telemetry",
            "app.modules.runs.domain.policies",
        ),
    )
    assert violations == []


def test_execution_plane_does_not_import_framework_specific_runtime_packages() -> None:
    violations = _collect_forbidden_imports(
        base_dir=Path("app/execution"),
        forbidden_prefixes=(
            "agent_atlas_runner_openai_agents",
            "agent_atlas_runner_langgraph",
        ),
    )
    assert violations == []


def test_execution_plane_does_not_import_run_runtime_translation_helpers() -> None:
    violations = _collect_forbidden_imports(
        base_dir=Path("app/execution"),
        forbidden_prefixes=("app.modules.runs.application.runtime_translation",),
    )
    assert violations == []


def test_non_execution_packages_do_not_import_execution_service_compatibility_module():
    violations = _collect_forbidden_imports(
        base_dir=Path("app"),
        forbidden_prefixes=("app.execution.service",),
        allowed_paths=(Path("app/execution"),),
    )
    assert violations == []


def test_feature_contract_compatibility_modules_have_been_removed() -> None:
    compatibility_modules = sorted(Path("app/modules").rglob("contracts/*.py"))
    assert compatibility_modules == []


def test_framework_runtime_compatibility_shims_have_been_removed() -> None:
    compatibility_modules = (
        BACKEND_ROOT / "app/infrastructure/adapters/langchain/runtime.py",
        BACKEND_ROOT / "app/infrastructure/adapters/langchain/trace_mapper.py",
        BACKEND_ROOT / "app/infrastructure/adapters/openai_agents/runtime.py",
        BACKEND_ROOT / "app/infrastructure/adapters/openai_agents/trace_mapper.py",
    )
    assert all(not path.exists() for path in compatibility_modules)


def test_legacy_runs_telemetry_paths_have_been_removed():
    legacy_paths = (
        BACKEND_ROOT / "app/modules/runs/application/telemetry.py",
        BACKEND_ROOT / "app/modules/runs/adapters/outbound/telemetry/trace_projector.py",
        BACKEND_ROOT / "app/modules/runs/adapters/outbound/telemetry/trajectory_projector.py",
    )
    assert all(not path.exists() for path in legacy_paths)


def test_legacy_tracing_package_has_been_removed():
    legacy_paths = (
        BACKEND_ROOT / "app/tracing/__init__.py",
        BACKEND_ROOT / "app/tracing/ports.py",
        BACKEND_ROOT / "app/tracing/backends/phoenix.py",
        BACKEND_ROOT / "app/tracing/exporters/otlp.py",
    )
    assert all(not path.exists() for path in legacy_paths)


def _collect_forbidden_imports(
    *,
    base_dir: Path,
    forbidden_prefixes: tuple[str, ...],
    allowed_paths: tuple[Path, ...] = (),
    required_layer: str | None = None,
) -> list[str]:
    violations: list[str] = []
    for path in sorted(base_dir.rglob("*.py")):
        if any(path.is_relative_to(allowed_path) for allowed_path in allowed_paths):
            continue
        if required_layer is not None and _module_layer(path) != required_layer:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module] if node.module else []
            else:
                continue

            for name in names:
                if name and any(
                    name == forbidden or name.startswith(f"{forbidden}.")
                    for forbidden in forbidden_prefixes
                ):
                    violations.append(f"{path}:{node.lineno}:{name}")
    return violations


def _module_layer(path: Path) -> str | None:
    parts = path.parts
    try:
        modules_index = parts.index("modules")
    except ValueError:
        return None

    layer_index = modules_index + 2
    if layer_index >= len(parts):
        return None
    return parts[layer_index]


def _collect_cross_feature_application_imports(*, base_dir: Path) -> list[str]:
    violations: list[str] = []
    for path in sorted(base_dir.rglob("*.py")):
        parts = path.parts
        try:
            current_feature = parts[parts.index("modules") + 1]
        except (ValueError, IndexError):
            continue

        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module] if node.module else []
            else:
                continue

            for name in names:
                if not name or not name.startswith("app.modules."):
                    continue
                imported_parts = name.split(".")
                if len(imported_parts) < 5:
                    continue
                imported_feature = imported_parts[2]
                imported_layer = ".".join(imported_parts[3:5])
                if imported_feature == current_feature:
                    continue
                if imported_layer in {"application.use_cases", "application.execution"}:
                    violations.append(f"{path}:{node.lineno}:{name}")

    return violations
