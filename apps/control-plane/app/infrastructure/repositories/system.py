from __future__ import annotations

from app.infrastructure.repositories.common import (
    PlaneStoreSetSource,
    resolve_state_store,
    state_store_container,
)
from app.infrastructure.storage import build_storage_contributors


class StateSystemStatus:
    def __init__(self, stores: PlaneStoreSetSource = None) -> None:
        self._stores_source = stores

    def state_initialized(self) -> bool:
        return True

    def persistence_enabled(self) -> bool:
        return bool(resolve_state_store(self._stores_source).enabled)


def reset_state() -> None:
    stores = state_store_container.rebuild()
    for contributor in build_storage_contributors(stores):
        contributor.init_schema()
        contributor.reset_state()


__all__ = ["StateSystemStatus", "reset_state"]
