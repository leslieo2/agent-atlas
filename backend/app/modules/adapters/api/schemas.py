from __future__ import annotations

from pydantic import BaseModel

from app.modules.adapters.domain.models import AdapterDescriptor
from app.modules.shared.domain.enums import AdapterKind


class AdapterDescriptorResponse(BaseModel):
    kind: AdapterKind
    name: str
    runtime_version: str
    notes: str
    supports_replay: bool = True
    supports_eval: bool = True

    @classmethod
    def from_domain(cls, adapter: AdapterDescriptor) -> AdapterDescriptorResponse:
        return cls.model_validate(adapter.model_dump())
