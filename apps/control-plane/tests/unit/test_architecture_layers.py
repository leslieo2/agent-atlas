from __future__ import annotations

import ast
from pathlib import Path


def test_domain_layers_do_not_import_upward_dependencies() -> None:
    violations = _collect_layer_violations(
        base_dir=Path("app/modules"),
        source_layer="domain",
        forbidden_prefixes=(
            "fastapi",
            "app.api",
            "app.bootstrap",
            "app.db",
            "app.infrastructure",
        ),
        forbidden_module_layers=("contracts", "application"),
    )
    assert violations == []


def test_application_layers_do_not_import_contract_or_infrastructure_details() -> None:
    violations = _collect_layer_violations(
        base_dir=Path("app/modules"),
        source_layer="application",
        forbidden_prefixes=(
            "fastapi",
            "app.api",
            "app.bootstrap",
            "app.db",
            "app.infrastructure",
        ),
        forbidden_module_layers=("contracts",),
    )
    assert violations == []


def test_contract_layers_do_not_import_framework_or_infrastructure_details() -> None:
    violations = _collect_layer_violations(
        base_dir=Path("app/modules"),
        source_layer="contracts",
        forbidden_prefixes=(
            "fastapi",
            "app.api",
            "app.bootstrap",
            "app.db",
            "app.infrastructure",
        ),
        forbidden_module_layers=(),
    )
    assert violations == []


def test_domain_layers_do_not_import_other_feature_domains() -> None:
    violations = _collect_cross_feature_domain_imports(base_dir=Path("app/modules"))
    assert violations == []


def test_shared_module_does_not_depend_on_feature_modules() -> None:
    violations = _collect_shared_feature_violations(base_dir=Path("app/modules/shared"))
    assert violations == []


def test_runs_domain_does_not_import_execution_plane() -> None:
    violations = _collect_import_prefix_violations(
        base_dir=Path("app/modules/runs/domain"),
        forbidden_prefixes=("app.execution",),
    )
    assert violations == []


def test_shared_and_agent_domain_surfaces_do_not_reexport_contract_models() -> None:
    boundary_files = (
        Path("app/modules/shared/domain/__init__.py"),
        Path("app/modules/shared/domain/execution.py"),
        Path("app/modules/shared/domain/models.py"),
        Path("app/modules/shared/domain/observability.py"),
        Path("app/modules/shared/domain/traces.py"),
        Path("app/modules/agents/domain/__init__.py"),
    )

    violations: list[str] = []
    for path in boundary_files:
        violations.extend(_collect_contract_reexports(path))

    assert violations == []


def test_execution_contracts_module_does_not_shadow_execution_owned_control_records() -> None:
    path = Path("app/execution/contracts.py")
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    forbidden_classes = {
        "Heartbeat",
        "RunHandle",
        "RunTerminalSummary",
        "RunStatusSnapshot",
        "CancelRequest",
        "ExecutionCapability",
    }

    violations: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name in forbidden_classes:
            violations.append(f"{path}:{node.lineno}:{node.name}")
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "ExecutionRunSpec":
                    violations.append(f"{path}:{node.lineno}:ExecutionRunSpec")

    assert violations == []


def test_trace_runtime_translation_does_not_rebuild_contract_events_locally() -> None:
    violations: list[str] = []
    for path in sorted(Path("app").rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        if "TraceIngestEvent.model_validate(event.model_dump(" in text:
            violations.append(str(path))

    assert violations == []


def _collect_layer_violations(
    *,
    base_dir: Path,
    source_layer: str,
    forbidden_prefixes: tuple[str, ...],
    forbidden_module_layers: tuple[str, ...],
) -> list[str]:
    violations: list[str] = []

    for path in sorted(base_dir.rglob("*.py")):
        if _module_layer(path) != source_layer:
            continue

        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for name, lineno in _iter_imports(tree):
            if any(
                name == prefix or name.startswith(f"{prefix}.") for prefix in forbidden_prefixes
            ):
                violations.append(f"{path}:{lineno}:{name}")
                continue

            imported_layer = _module_layer_from_import(name)
            if imported_layer in forbidden_module_layers:
                violations.append(f"{path}:{lineno}:{name}")

    return violations


def _collect_import_prefix_violations(
    *,
    base_dir: Path,
    forbidden_prefixes: tuple[str, ...],
) -> list[str]:
    violations: list[str] = []

    for path in sorted(base_dir.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for name, lineno in _iter_imports(tree):
            if any(
                name == prefix or name.startswith(f"{prefix}.") for prefix in forbidden_prefixes
            ):
                violations.append(f"{path}:{lineno}:{name}")

    return violations


def _collect_shared_feature_violations(*, base_dir: Path) -> list[str]:
    violations: list[str] = []

    for path in sorted(base_dir.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for name, lineno in _iter_imports(tree):
            if not name.startswith("app.modules.") or name.startswith("app.modules.shared."):
                continue
            violations.append(f"{path}:{lineno}:{name}")

    return violations


def _collect_contract_reexports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imported_contract_names: set[str] = set()
    exported_names: set[str] = set()

    for node in tree.body:
        if (
            isinstance(node, ast.ImportFrom)
            and node.module
            and node.module.startswith("agent_atlas_contracts.")
        ):
            for alias in node.names:
                imported_contract_names.add(alias.asname or alias.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__all__":
                    exported_names.update(_string_literals(node.value))

    return [f"{path}:{name}" for name in sorted(imported_contract_names & exported_names)]


def _string_literals(node: ast.AST) -> set[str]:
    if isinstance(node, ast.List | ast.Tuple | ast.Set):
        return {
            element.value
            for element in node.elts
            if isinstance(element, ast.Constant) and isinstance(element.value, str)
        }
    return set()


def _collect_cross_feature_domain_imports(*, base_dir: Path) -> list[str]:
    violations: list[str] = []

    for path in sorted(base_dir.rglob("*.py")):
        if _module_layer(path) != "domain":
            continue

        parts = path.parts
        try:
            current_feature = parts[parts.index("modules") + 1]
        except (ValueError, IndexError):
            continue

        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for name, lineno in _iter_imports(tree):
            if not name.startswith("app.modules."):
                continue

            imported_parts = name.split(".")
            if len(imported_parts) < 4:
                continue

            imported_feature = imported_parts[2]
            imported_layer = imported_parts[3]
            if imported_layer != "domain":
                continue
            if imported_feature in {current_feature, "shared"}:
                continue

            violations.append(f"{path}:{lineno}:{name}")

    return violations


def _iter_imports(tree: ast.AST) -> list[tuple[str, int]]:
    imports: list[tuple[str, int]] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend((alias.name, node.lineno) for alias in node.names if alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append((node.module, node.lineno))

    return imports


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


def _module_layer_from_import(name: str) -> str | None:
    parts = name.split(".")
    if len(parts) < 4 or parts[:2] != ["app", "modules"]:
        return None
    return parts[3]
