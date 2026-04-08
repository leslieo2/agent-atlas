from __future__ import annotations

from typing import Protocol

from app.db.persistence import PlaneStoreSet, build_plane_store_set, to_uuid


class _SupportsPlaneStoreSet(Protocol):
    @property
    def current(self) -> PlaneStoreSet: ...


PlaneStoreSetSource = PlaneStoreSet | _SupportsPlaneStoreSet | None


class StateStoreContainer:
    def __init__(self) -> None:
        self._stores = build_plane_store_set()

    @property
    def current(self) -> PlaneStoreSet:
        return self._stores

    @property
    def enabled(self) -> bool:
        return self._stores.enabled

    def rebuild(self) -> PlaneStoreSet:
        self._stores.close()
        self._stores = build_plane_store_set()
        return self._stores


state_store_container = StateStoreContainer()


def resolve_state_store(source: PlaneStoreSetSource = None) -> PlaneStoreSet:
    if source is None:
        return state_store_container.current
    if isinstance(source, PlaneStoreSet):
        return source
    return source.current


__all__ = [
    "PlaneStoreSetSource",
    "StateStoreContainer",
    "resolve_state_store",
    "state_store_container",
    "to_uuid",
]
