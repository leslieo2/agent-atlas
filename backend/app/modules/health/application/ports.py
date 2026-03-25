from __future__ import annotations

from typing import Protocol


class SystemStatusPort(Protocol):
    def state_initialized(self) -> bool: ...

    def persistence_enabled(self) -> bool: ...
