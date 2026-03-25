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
        forbidden_module_layers=("api", "application"),
    )
    assert violations == []


def test_application_layers_do_not_import_api_or_infrastructure_details() -> None:
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
        forbidden_module_layers=("api",),
    )
    assert violations == []


def test_shared_module_does_not_depend_on_feature_modules() -> None:
    violations = _collect_shared_feature_violations(base_dir=Path("app/modules/shared"))
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
            if any(name == prefix or name.startswith(f"{prefix}.") for prefix in forbidden_prefixes):
                violations.append(f"{path}:{lineno}:{name}")
                continue

            imported_layer = _module_layer_from_import(name)
            if imported_layer in forbidden_module_layers:
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
