from __future__ import annotations

from typing import Protocol

from app.modules.adapters.domain.models import AdapterDescriptor


class AdapterCatalogPort(Protocol):
    def list_adapters(self) -> list[AdapterDescriptor]: ...
