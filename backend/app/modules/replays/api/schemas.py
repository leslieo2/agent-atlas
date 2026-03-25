from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.modules.replays.domain.models import ReplayRequest as DomainReplayRequest
from app.modules.replays.domain.models import ReplayResult


class ReplayRequest(BaseModel):
    run_id: UUID
    step_id: str
    edited_prompt: str | None = None
    model: str | None = None
    tool_overrides: dict[str, object] = Field(default_factory=dict)
    rationale: str | None = None

    def to_domain(self) -> DomainReplayRequest:
        return DomainReplayRequest.model_validate(self.model_dump())


class ReplayResponse(BaseModel):
    replay_id: UUID
    run_id: UUID
    step_id: str
    baseline_output: str
    replay_output: str
    diff: str
    updated_prompt: str | None
    model: str
    temperature: float
    started_at: datetime

    @classmethod
    def from_domain(cls, replay: ReplayResult) -> ReplayResponse:
        return cls.model_validate(replay.model_dump())
