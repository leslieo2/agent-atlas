from __future__ import annotations

from app.modules.adapters.application.ports import AdapterCatalogPort
from app.modules.adapters.domain.models import AdapterDescriptor


class AdapterQueries:
    def __init__(self, adapter_catalog: AdapterCatalogPort) -> None:
        self.adapter_catalog = adapter_catalog

    def list_adapters(self) -> list[AdapterDescriptor]:
        return self.adapter_catalog.list_adapters()
