from __future__ import annotations

import ast
from pathlib import Path


def test_runtime_packages_do_not_import_control_plane_modules() -> None:
    runtimes_dir = Path(__file__).resolve().parents[3] / "runtimes"
    violations: list[str] = []

    for path in sorted(runtimes_dir.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for name, lineno in _iter_imports(tree):
            if name == "app" or name.startswith("app."):
                violations.append(f"{path}:{lineno}:{name}")

    assert violations == []


def _iter_imports(tree: ast.AST) -> list[tuple[str, int]]:
    imports: list[tuple[str, int]] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend((alias.name, node.lineno) for alias in node.names if alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append((node.module, node.lineno))

    return imports
