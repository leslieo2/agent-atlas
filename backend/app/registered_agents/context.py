from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID


@dataclass(frozen=True)
class RegisteredAgentBuildContext:
    run_id: UUID
    project: str
    dataset: str | None
    prompt: str
    tags: list[str] = field(default_factory=list)
    project_metadata: dict[str, Any] = field(default_factory=dict)
