from __future__ import annotations

from app.modules.shared.application.contracts import RunRepository, RunTraceLookup


class StateRunTraceLookup:
    def __init__(self, run_repository: RunRepository) -> None:
        self.run_repository = run_repository

    def get(self, run_id):
        run = self.run_repository.get(run_id)
        if run is None:
            return None
        return RunTraceLookup(
            run_id=run.run_id,
            created_at=run.created_at,
        )


__all__ = ["StateRunTraceLookup"]
