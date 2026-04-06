from __future__ import annotations

import json
from pathlib import Path

from app.modules.datasets.domain.models import DatasetCreate, DatasetSample

CLAUDE_CODE_STARTER_DATASET_NAME = "claude-code-code-edit"
CLAUDE_CODE_STARTER_DATASET_VERSION = "v1"
CLAUDE_CODE_STARTER_DATASET_SOURCE = "claude-code-code-edit-v1"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[6]


def _claude_code_starter_dataset_path() -> Path:
    return _repo_root() / "apps" / "control-plane" / "datasets" / "claude-code-code-edit-v1.jsonl"


def _parse_dataset_rows(path: Path) -> list[DatasetSample]:
    rows: list[DatasetSample] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        rows.append(DatasetSample.model_validate(json.loads(line)))
    return rows


def claude_code_starter_dataset_create() -> DatasetCreate:
    return DatasetCreate(
        name=CLAUDE_CODE_STARTER_DATASET_NAME,
        description=(
            "Bundled code-edit evaluation dataset aligned with the "
            "Claude Code starter's mounted sample project."
        ),
        source=CLAUDE_CODE_STARTER_DATASET_SOURCE,
        version=CLAUDE_CODE_STARTER_DATASET_VERSION,
        rows=_parse_dataset_rows(_claude_code_starter_dataset_path()),
    )
