from __future__ import annotations

from pydantic import BaseModel

from app.modules.shared.domain.enums import AdapterKind


class AdapterDescriptor(BaseModel):
    kind: AdapterKind
    name: str
    runtime_version: str
    notes: str
    supports_replay: bool = True
    supports_eval: bool = True
